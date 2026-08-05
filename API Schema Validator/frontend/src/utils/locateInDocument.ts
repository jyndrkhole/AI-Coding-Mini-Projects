/**
 * Accurate editor location using YAML/JSON AST path walks.
 * Avoids naive first-match text search (e.g. wrong `enum:` elsewhere).
 */

import {
  isMap,
  isPair,
  isScalar,
  isSeq,
  parseDocument,
  type Document,
  type Node,
  type Pair,
  type YAMLMap,
} from 'yaml';

export interface SchemaLocateContext {
  /** OpenAPI path e.g. /pets/{petId} */
  openApiPath?: string | null;
  /** HTTP method e.g. GET */
  method?: string | null;
  /** Response status e.g. 200 */
  statusCode?: string | null;
  /** components/schemas name when selected */
  schemaName?: string | null;
}

function offsetToLine(text: string, offset: number | undefined | null): number | null {
  if (offset == null || offset < 0 || !text) return null;
  let line = 1;
  const max = Math.min(offset, text.length);
  for (let i = 0; i < max; i += 1) {
    if (text.charCodeAt(i) === 10) line += 1;
  }
  return line;
}

function nodeStartOffset(node: Node | null | undefined): number | null {
  if (!node) return null;
  if (typeof node.range?.[0] === 'number') return node.range[0];
  return null;
}

function nodeLine(text: string, node: Node | null | undefined): number | null {
  return offsetToLine(text, nodeStartOffset(node));
}

export function pathSegments(path: string | null | undefined): string[] {
  if (!path || path === '$' || path === '/') return [];

  if (path.startsWith('$')) {
    return path
      .replace(/^\$\.?/, '')
      .replace(/\[(\d+)\]/g, '.$1')
      .split('.')
      .map((s) => decodeURIComponent(s.trim()))
      .filter(Boolean);
  }

  return path
    .split('/')
    .map((s) => {
      const t = s.trim();
      if (!t) return '';
      return decodeURIComponent(t.replace(/~1/g, '/').replace(/~0/g, '~'));
    })
    .filter(Boolean);
}

function scalarKey(value: unknown): string | null {
  if (isScalar(value)) return String(value.value);
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return null;
}

function mapGet(map: YAMLMap, key: string): { pair: Pair; value: Node | null } | null {
  for (const item of map.items) {
    if (!isPair(item)) continue;
    const k = scalarKey(item.key);
    if (k === key) {
      return { pair: item, value: (item.value as Node) ?? null };
    }
  }
  // Case-insensitive fallback for HTTP methods / media types
  const lower = key.toLowerCase();
  for (const item of map.items) {
    if (!isPair(item)) continue;
    const k = scalarKey(item.key);
    if (k && k.toLowerCase() === lower) {
      return { pair: item, value: (item.value as Node) ?? null };
    }
  }
  return null;
}

type WalkResult = {
  node: Node | null;
  /** Prefer highlighting the key (e.g. `enum:`) over the value */
  keyNode: Node | null;
};

/**
 * Walk a YAML subtree by schema/JSON path segments.
 * For map keys, keyNode points at the property name so we can highlight `enum:`.
 */
function walkPath(root: Node | null, segments: string[]): WalkResult | null {
  if (!root) return null;
  let current: Node | null = root;
  let keyNode: Node | null = null;

  for (const segment of segments) {
    if (!current) return null;

    if (isMap(current)) {
      const found = mapGet(current, segment);
      if (!found) return null;
      keyNode = (found.pair.key as Node) ?? null;
      current = found.value;
      continue;
    }

    if (isSeq(current)) {
      const idx = Number(segment);
      if (!Number.isInteger(idx) || idx < 0 || idx >= current.items.length) return null;
      keyNode = null;
      current = (current.items[idx] as Node) ?? null;
      continue;
    }

    return null;
  }

  return { node: current, keyNode };
}

function highlightLine(text: string, walked: WalkResult | null): number | null {
  if (!walked) return null;
  // Prefer the key line (`enum:`) so users land on the constraint, not deep array values.
  return nodeLine(text, walked.keyNode) ?? nodeLine(text, walked.node);
}

function followRef(doc: Document, refNode: Node | null): Node | null {
  if (!isMap(refNode)) return refNode;
  const ref = mapGet(refNode, '$ref');
  if (!ref || !isScalar(ref.value)) return refNode;
  const refStr = String(ref.value.value);
  if (!refStr.startsWith('#/')) return refNode;

  const segs = refStr
    .replace(/^#\//, '')
    .split('/')
    .map((s) => s.replace(/~1/g, '/').replace(/~0/g, '~'));
  const target = walkPath(doc.contents as Node, segs);
  return target?.node ?? refNode;
}

function preferJsonMediaSchema(contentMap: YAMLMap): Node | null {
  const preferred = ['application/json', 'application/vnd.api+json', 'text/json'];
  for (const mt of preferred) {
    const media = mapGet(contentMap, mt);
    if (media?.value && isMap(media.value)) {
      const schema = mapGet(media.value, 'schema');
      if (schema) return schema.value;
    }
  }
  for (const item of contentMap.items) {
    if (!isPair(item) || !isMap(item.value)) continue;
    const schema = mapGet(item.value, 'schema');
    if (schema) return schema.value;
  }
  return null;
}

/**
 * Locate the JSON Schema node that validation was run against inside an
 * OpenAPI document (operation response schema or components schema).
 */
function resolveOpenApiSchemaRoot(
  doc: Document,
  ctx: SchemaLocateContext,
): Node | null {
  const root = doc.contents as Node;
  if (!isMap(root)) return root;

  if (ctx.schemaName) {
    const named = walkPath(root, ['components', 'schemas', ctx.schemaName]);
    if (named?.node) return named.node;
    const swaggerDefs = walkPath(root, ['definitions', ctx.schemaName]);
    if (swaggerDefs?.node) return swaggerDefs.node;
  }

  if (ctx.openApiPath && ctx.method) {
    const status = ctx.statusCode || '200';
    let operation =
      walkPath(root, ['paths', ctx.openApiPath, ctx.method.toLowerCase()])?.node ??
      walkPath(root, ['paths', ctx.openApiPath, ctx.method.toUpperCase()])?.node ??
      null;

    if (operation && isMap(operation)) {
      const responses = mapGet(operation, 'responses')?.value;
      if (responses && isMap(responses)) {
        const response =
          mapGet(responses, String(status))?.value ||
          mapGet(responses, 'default')?.value ||
          null;
        if (response && isMap(response)) {
          const content = mapGet(response, 'content')?.value;
          if (content && isMap(content)) {
            return followRef(doc, preferJsonMediaSchema(content));
          }
          return followRef(doc, mapGet(response, 'schema')?.value ?? null);
        }
      }
    }
  }

  return null;
}

function isLikelyOpenApi(doc: Document): boolean {
  const root = doc.contents;
  if (!isMap(root)) return false;
  return Boolean(mapGet(root, 'openapi') || mapGet(root, 'swagger') || mapGet(root, 'paths'));
}

function parseDoc(text: string): Document | null {
  try {
    return parseDocument(text, {
      keepSourceTokens: true,
      uniqueKeys: false,
    });
  } catch {
    return null;
  }
}

/** Remove validator-bundling prefixes like $defs / definitions from a path. */
function stripBundledPrefixes(segments: string[]): string[] {
  const out = [...segments];
  while (out.length >= 2) {
    if (out[0] === 'components' && out[1] === 'schemas' && out.length >= 3) {
      out.splice(0, 3);
      continue;
    }
    if (out[0] === '$defs' || out[0] === 'definitions') {
      out.splice(0, 2);
      continue;
    }
    break;
  }
  return out;
}

function tryWalk(
  text: string,
  root: Node | null,
  segments: string[],
): number | null {
  if (!segments.length) return nodeLine(text, root);

  const direct = highlightLine(text, walkPath(root, segments));
  if (direct) return direct;

  const stripped = stripBundledPrefixes(segments);
  if (stripped.length !== segments.length) {
    return highlightLine(text, walkPath(root, stripped));
  }
  return null;
}

/**
 * Resolve a schema_path to a 1-based line.
 * Uses AST walks scoped to the selected OpenAPI schema, with fallbacks that
 * combine json_path (instance field) + the failing keyword (enum/format/type).
 */
export function resolveSchemaLine(
  schemaText: string,
  schemaPath: string | null | undefined,
  ctx: SchemaLocateContext = {},
  jsonPath?: string | null,
): number | null {
  if (!schemaText?.trim()) return null;
  const doc = parseDoc(schemaText);
  if (!doc) return null;

  const root = doc.contents as Node;
  const candidates = buildSchemaPathCandidates(schemaPath, jsonPath);

  const roots: Array<Node | null> = [];
  if (isLikelyOpenApi(doc)) {
    roots.push(resolveOpenApiSchemaRoot(doc, ctx));

    const components = walkPath(root, ['components', 'schemas']);
    if (components?.node && isMap(components.node)) {
      for (const item of components.node.items) {
        if (isPair(item) && item.value) roots.push(item.value as Node);
      }
    }
  }
  roots.push(root);

  for (const schemaRoot of roots) {
    if (!schemaRoot) continue;
    for (const segments of candidates) {
      const line = tryWalk(schemaText, schemaRoot, segments);
      if (line) return line;
    }
  }

  return null;
}

function buildSchemaPathCandidates(
  schemaPath: string | null | undefined,
  jsonPath?: string | null,
): string[][] {
  const schemaSegs = pathSegments(schemaPath);
  const jsonSegs = pathSegments(jsonPath);
  const out: string[][] = [];

  const push = (segs: string[]) => {
    if (!segs.length) return;
    const key = segs.join('/');
    if (!out.some((s) => s.join('/') === key)) out.push(segs);
  };

  push(schemaSegs);
  push(stripBundledPrefixes(schemaSegs));

  // $.a.b + keyword `format` → properties/a/properties/b/format
  const keyword = schemaSegs.length ? schemaSegs[schemaSegs.length - 1] : null;
  if (jsonSegs.length) {
    const propsChain: string[] = [];
    for (const seg of jsonSegs) {
      if (/^\d+$/.test(seg)) {
        propsChain.push('items');
      } else {
        propsChain.push('properties', seg);
      }
    }
    push(propsChain);
    if (keyword) push([...propsChain, keyword]);

    // Also try last property only (common for $ref-inlined leaves)
    const lastProp = [...jsonSegs].reverse().find((s) => !/^\d+$/.test(s));
    if (lastProp) {
      push(['properties', lastProp]);
      if (keyword) push(['properties', lastProp, keyword]);
    }
  }

  return out;
}

/** Prefer AST json_path walk; fall back to backend line_number. */
export function resolveResponseLine(
  responseText: string,
  jsonPath: string | null | undefined,
  lineNumber?: number | null,
): number | null {
  const astLine = locateJsonPathLine(responseText, jsonPath);
  if (astLine) return astLine;
  if (typeof lineNumber === 'number' && lineNumber > 0) return lineNumber;
  return null;
}

function locateJsonPathLine(
  text: string,
  jsonPath: string | null | undefined,
): number | null {
  if (!text?.trim()) return null;
  const doc = parseDoc(text);
  if (!doc) return null;
  const segments = pathSegments(jsonPath);
  if (!segments.length) return 1;
  return highlightLine(text, walkPath(doc.contents as Node, segments));
}

export function findLineForPath(
  documentText: string,
  path: string | null | undefined,
): number | null {
  return locateJsonPathLine(documentText, path);
}
