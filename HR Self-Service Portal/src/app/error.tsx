"use client";

export default function AppError({ reset }: { error: Error; reset: () => void }) {
  return (
    <main className="mx-auto flex min-h-full max-w-lg flex-col justify-center px-6 py-16">
      <p className="text-sm font-medium text-brand">PeopleHub</p>
      <h1 className="mt-2 text-2xl font-semibold text-ink">Something went wrong</h1>
      <p className="mt-2 text-sm text-muted">
        Try again. If this keeps happening, contact your administrator.
      </p>
      <button
        type="button"
        onClick={reset}
        className="mt-6 h-10 w-fit rounded-lg bg-brand px-4 text-sm font-medium text-white"
      >
        Try again
      </button>
    </main>
  );
}
