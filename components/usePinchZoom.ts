"use client";

import { useCallback, useEffect, useRef } from "react";
import type { RefObject } from "react";

export const MIN_ZOOM = 0.5;
export const MAX_ZOOM = 4;
const clampZoom = (z: number) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z));

// Mouse wheels report in lines or pages, trackpads in pixels.
const WHEEL_UNITS = [1, 16, 400];
// How long the wheel must stay quiet before a trackpad pinch counts as done.
const WHEEL_END_MS = 150;

interface Gesture {
  startZoom: number;
  factor: number;
  // Point under the fingers/cursor, in viewport coordinates, and the same
  // point relative to the page box when the gesture started.
  clientX: number;
  clientY: number;
  relX: number;
  relY: number;
}

interface PendingAnchor {
  clientX: number;
  clientY: number;
  relX: number;
  relY: number;
  ratio: number;
}

/**
 * Pinch-to-zoom on the page, centered where the fingers (or the cursor) are,
 * instead of the browser's own pinch-zoom of the whole interface.
 *
 * During the gesture the page is only scaled with a CSS transform (instant).
 * When it ends, `setZoom` asks PdfPage for a crisp rendering at the new size;
 * `afterRender` (wired to PdfPage's `onRendered`) then drops the transform
 * and scrolls so the point that was under the fingers stays there.
 *
 * Sources: two-finger touch (phones, tablets), ctrl+wheel (trackpad pinch in
 * Chrome/Firefox/Edge, and ctrl+mouse wheel), Safari's own `gesture*` events
 * (trackpad pinch on macOS Safari).
 */
export function usePinchZoom(
  containerRef: RefObject<HTMLDivElement | null>,
  zoom: number,
  setZoom: (zoom: number) => void,
  enabled: boolean,
) {
  const zoomRef = useRef(zoom);
  zoomRef.current = zoom;
  const pendingRef = useRef<PendingAnchor | null>(null);

  const afterRender = useCallback(() => {
    const container = containerRef.current;
    const page = container?.querySelector<HTMLElement>(".pdf-page");
    if (!container || !page) return;
    page.style.transform = "";
    const anchor = pendingRef.current;
    pendingRef.current = null;
    if (!anchor) return;
    const rect = page.getBoundingClientRect();
    container.scrollLeft += rect.left - (anchor.clientX - anchor.relX * anchor.ratio);
    container.scrollTop += rect.top - (anchor.clientY - anchor.relY * anchor.ratio);
  }, [containerRef]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !enabled) return;

    let gesture: Gesture | null = null;
    let touchStartDistance = 0;
    let touchActive = false;
    let wheelTimer: ReturnType<typeof setTimeout> | undefined;

    const page = () => container.querySelector<HTMLElement>(".pdf-page");

    const begin = (clientX: number, clientY: number): boolean => {
      // The previous gesture's rendering hasn't landed yet: its preview
      // transform is still on the page, so measuring now would be wrong.
      const el = page();
      if (!el || pendingRef.current) return false;
      const rect = el.getBoundingClientRect();
      gesture = {
        startZoom: zoomRef.current,
        factor: 1,
        clientX,
        clientY,
        relX: clientX - rect.left,
        relY: clientY - rect.top,
      };
      el.style.transformOrigin = `${gesture.relX}px ${gesture.relY}px`;
      return true;
    };

    const update = (factor: number) => {
      const el = page();
      if (!gesture || !el) return;
      gesture.factor = clampZoom(gesture.startZoom * factor) / gesture.startZoom;
      el.style.transform = `scale(${gesture.factor})`;
    };

    const end = () => {
      const g = gesture;
      gesture = null;
      if (!g) return;
      const next = clampZoom(g.startZoom * g.factor);
      if (Math.abs(next - g.startZoom) < 0.01) {
        const el = page();
        if (el) el.style.transform = "";
        return;
      }
      pendingRef.current = { clientX: g.clientX, clientY: g.clientY, relX: g.relX, relY: g.relY, ratio: next / g.startZoom };
      setZoom(next);
    };

    const distance = (t: TouchList) => Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY);

    const onTouchStart = (e: TouchEvent) => {
      if (e.touches.length !== 2) return;
      touchActive = true;
      const x = (e.touches[0].clientX + e.touches[1].clientX) / 2;
      const y = (e.touches[0].clientY + e.touches[1].clientY) / 2;
      if (begin(x, y)) touchStartDistance = distance(e.touches);
    };
    const onTouchMove = (e: TouchEvent) => {
      if (!gesture || e.touches.length !== 2) return;
      e.preventDefault(); // no native page zoom while we handle it
      update(distance(e.touches) / touchStartDistance);
    };
    const onTouchEnd = (e: TouchEvent) => {
      if (e.touches.length < 2) {
        touchActive = false;
        end();
      }
    };

    const onWheel = (e: WheelEvent) => {
      if (!e.ctrlKey) return; // plain scrolling stays scrolling
      e.preventDefault(); // no browser zoom of the whole interface
      if (!gesture && !begin(e.clientX, e.clientY)) return;
      const deltaY = e.deltaY * (WHEEL_UNITS[e.deltaMode] ?? 1);
      update(gesture ? (gesture.factor * Math.exp(-deltaY * 0.01)) : 1);
      clearTimeout(wheelTimer);
      wheelTimer = setTimeout(end, WHEEL_END_MS);
    };

    // Safari only (not in the DOM typings): `scale` is relative to the start.
    type SafariGesture = Event & { scale: number; clientX: number; clientY: number };
    const onGestureStart = (e: Event) => {
      e.preventDefault();
      if (touchActive) return; // iOS also fires these alongside touch events
      const g = e as SafariGesture;
      begin(g.clientX, g.clientY);
    };
    const onGestureChange = (e: Event) => {
      e.preventDefault();
      if (touchActive) return;
      update((e as SafariGesture).scale);
    };
    const onGestureEnd = (e: Event) => {
      e.preventDefault();
      if (!touchActive) end();
    };

    container.addEventListener("touchstart", onTouchStart, { passive: true });
    container.addEventListener("touchmove", onTouchMove, { passive: false });
    container.addEventListener("touchend", onTouchEnd);
    container.addEventListener("touchcancel", onTouchEnd);
    container.addEventListener("wheel", onWheel, { passive: false });
    container.addEventListener("gesturestart", onGestureStart);
    container.addEventListener("gesturechange", onGestureChange);
    container.addEventListener("gestureend", onGestureEnd);
    return () => {
      clearTimeout(wheelTimer);
      container.removeEventListener("touchstart", onTouchStart);
      container.removeEventListener("touchmove", onTouchMove);
      container.removeEventListener("touchend", onTouchEnd);
      container.removeEventListener("touchcancel", onTouchEnd);
      container.removeEventListener("wheel", onWheel);
      container.removeEventListener("gesturestart", onGestureStart);
      container.removeEventListener("gesturechange", onGestureChange);
      container.removeEventListener("gestureend", onGestureEnd);
    };
  }, [containerRef, enabled, setZoom]);

  return { afterRender };
}
