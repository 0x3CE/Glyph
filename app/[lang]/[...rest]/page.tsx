import { notFound } from "next/navigation";

// Any URL that isn't a real page lands here (proxy.ts rewrites unknown French
// paths to /fr/...), so it gets the localized 404 inside the [lang] layout
// with a real 404 status.
export default function CatchAll() {
  notFound();
}
