"use client";

import { ChevronDown, ChevronLeft, ChevronRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function CalendarMonthYear({
  basePath,
  year,
  month,
  monthName,
  years,
}: {
  basePath: string;
  year: number;
  month: number;
  monthName: string;
  years: number[];
}) {
  const router = useRouter();
  const rootRef = useRef<HTMLDivElement>(null);
  const panelId = useId();
  const [open, setOpen] = useState(false);
  const [viewYear, setViewYear] = useState(year);
  const firstYear = years[0] ?? year;
  const lastYear = years[years.length - 1] ?? year;

  useEffect(() => {
    setViewYear(year);
  }, [year]);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div className="relative" ref={rootRef}>
      <h2>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          aria-haspopup="dialog"
          className="inline-flex items-center gap-1 rounded-lg px-1 text-lg font-semibold text-ink hover:bg-canvas"
          onClick={() => {
            setViewYear(year);
            setOpen((value) => !value);
          }}
        >
          {monthName} {year}
          <ChevronDown className="h-4 w-4 text-muted" aria-hidden />
        </button>
      </h2>
      {open ? (
        <div
          id={panelId}
          role="dialog"
          aria-label="Choose month and year"
          className="absolute left-0 z-20 mt-2 w-64 rounded-xl border border-line bg-white p-3 shadow-sm"
        >
          <div className="mb-3 flex items-center justify-between">
            <button
              type="button"
              aria-label="Previous year"
              disabled={viewYear <= firstYear}
              className="grid h-8 w-8 place-items-center rounded-lg text-ink hover:bg-canvas disabled:cursor-not-allowed disabled:opacity-40"
              onClick={() => setViewYear((value) => value - 1)}
            >
              <ChevronLeft className="h-4 w-4" aria-hidden />
            </button>
            <p className="text-sm font-semibold">{viewYear}</p>
            <button
              type="button"
              aria-label="Next year"
              disabled={viewYear >= lastYear}
              className="grid h-8 w-8 place-items-center rounded-lg text-ink hover:bg-canvas disabled:cursor-not-allowed disabled:opacity-40"
              onClick={() => setViewYear((value) => value + 1)}
            >
              <ChevronRight className="h-4 w-4" aria-hidden />
            </button>
          </div>
          <div className="grid grid-cols-3 gap-1">
            {MONTHS.map((label, index) => {
              const value = index + 1;
              const selected = viewYear === year && value === month;
              return (
                <button
                  key={label}
                  type="button"
                  aria-pressed={selected}
                  className={
                    selected
                      ? "rounded-lg bg-brand px-2 py-2 text-sm font-medium text-white"
                      : "rounded-lg px-2 py-2 text-sm text-ink hover:bg-canvas"
                  }
                  onClick={() => {
                    setOpen(false);
                    if (viewYear !== year || value !== month) {
                      router.push(`${basePath}?year=${viewYear}&month=${value}`);
                    }
                  }}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}
