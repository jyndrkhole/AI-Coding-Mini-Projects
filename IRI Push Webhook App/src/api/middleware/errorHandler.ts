import type { ErrorRequestHandler, RequestHandler } from "express";

export const notFoundHandler: RequestHandler = (req, res) => {
  res.status(404).json({
    status: "error",
    message: `Not found: ${req.method} ${req.path}`
  });
};

export const errorHandler: ErrorRequestHandler = (err, _req, res, _next) => {
  const status = typeof err.status === "number" ? err.status : 500;
  const message = err instanceof Error ? err.message : "Unexpected error";
  res.status(status).json({
    status: "error",
    message
  });
};
