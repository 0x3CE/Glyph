import type { PageId } from "../registry";
import type { LocalizedContent } from "../types";
import { anonymize } from "./anonymize";
import { check } from "./check";
import { editText } from "./editText";
import { findReplace } from "./findReplace";
import { guideFixTypo, guideMac, guideWithoutAcrobat } from "./guides";
import { legalNotice } from "./legalNotice";
import { overlayVsReal } from "./overlayVsReal";
import { privacy } from "./privacy";
import { redact } from "./redact";
import { sign } from "./sign";
import { terms } from "./terms";

// Published pages: a page id gets a route, a sitemap entry and live internal
// links only once its content is listed here.
export const CONTENT: Partial<Record<PageId, LocalizedContent>> = {
  editText,
  overlayVsReal,
  redact,
  anonymize,
  check,
  findReplace,
  sign,
  guideFixTypo,
  guideWithoutAcrobat,
  guideMac,
  legalNotice,
  privacy,
  terms,
};

export const isPublished = (id: PageId): boolean => id in CONTENT;
