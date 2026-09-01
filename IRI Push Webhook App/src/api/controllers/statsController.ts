import type { RequestHandler } from "express";
import { getDashboardStats } from "../../repositories/webhookEventRepository.ts";

export const getStats: RequestHandler = (_req, res, next) => {
  try {
    res.json(getDashboardStats());
  } catch (error) {
    next(error);
  }
};
