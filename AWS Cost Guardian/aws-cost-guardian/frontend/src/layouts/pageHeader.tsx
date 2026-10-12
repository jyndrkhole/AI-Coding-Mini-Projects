import { createContext, useContext, useLayoutEffect, useMemo, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

type PageHeaderState = { title: string; subtitle?: string };

type PageHeaderContextValue = {
  header: PageHeaderState | null;
  setHeader: (header: PageHeaderState | null) => void;
  actionHost: HTMLElement | null;
  setActionHost: (node: HTMLElement | null) => void;
};

const PageHeaderContext = createContext<PageHeaderContextValue | null>(null);

export function PageHeaderProvider({ children }: { children: ReactNode }) {
  const [header, setHeader] = useState<PageHeaderState | null>(null);
  const [actionHost, setActionHost] = useState<HTMLElement | null>(null);
  const value = useMemo(() => ({ header, setHeader, actionHost, setActionHost }), [header, actionHost]);
  return <PageHeaderContext.Provider value={value}>{children}</PageHeaderContext.Provider>;
}

export function usePageHeader(title: string, subtitle?: string) {
  const setHeader = useContext(PageHeaderContext)?.setHeader;
  useLayoutEffect(() => {
    setHeader?.({ title, subtitle });
    return () => setHeader?.(null);
  }, [setHeader, title, subtitle]);
}

export function usePageHeaderContent() {
  return useContext(PageHeaderContext)?.header ?? null;
}

export function usePageHeaderHost() {
  return useContext(PageHeaderContext)?.setActionHost;
}

export function PageHeaderAction({ children }: { children: ReactNode }) {
  const actionHost = useContext(PageHeaderContext)?.actionHost;
  if (!actionHost) return null;
  return createPortal(children, actionHost);
}
