"use client";

import { useEffect } from "react";
import { confirmSessionAction, logoutAction, touchSessionAction } from "@/server/auth/actions";
import { SESSION_IDLE_MS } from "@/server/auth/timeout";

const TOUCH_EVERY_MS = 5 * 60 * 1000;

export function SessionIdle() {
  useEffect(() => {
    let idleTimer = 0;
    let lastTouch = 0;
    let stopped = false;

    const arm = () => {
      window.clearTimeout(idleTimer);
      idleTimer = window.setTimeout(() => {
        void onIdle();
      }, SESSION_IDLE_MS);
    };

    const onIdle = async () => {
      const alive = await confirmSessionAction().catch(() => false);
      if (stopped) return;
      if (alive) {
        arm();
        return;
      }
      const form = document.getElementById("session-idle-logout");
      if (form instanceof HTMLFormElement) form.requestSubmit();
    };

    const onActivity = () => {
      arm();
      if (Date.now() - lastTouch < TOUCH_EVERY_MS) return;
      lastTouch = Date.now();
      void touchSessionAction().catch(() => false);
    };

    arm();
    for (const eventName of ["pointerdown", "keydown", "scroll"]) {
      window.addEventListener(eventName, onActivity, { passive: true });
    }
    return () => {
      stopped = true;
      window.clearTimeout(idleTimer);
      for (const eventName of ["pointerdown", "keydown", "scroll"]) {
        window.removeEventListener(eventName, onActivity);
      }
    };
  }, []);

  return <form id="session-idle-logout" action={logoutAction} className="hidden" />;
}
