function csvCell(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }
  const text = String(value);
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

export function toCsv(headers: string[], rows: unknown[][]): string {
  const lines = [headers.map((header) => csvCell(header)).join(",")];
  for (const row of rows) {
    lines.push(row.map((cell) => csvCell(cell)).join(","));
  }
  return `\uFEFF${lines.join("\r\n")}\r\n`;
}
