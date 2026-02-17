"use client";

import { useState, useEffect, useRef } from "react";
import {
  analyzeContentQuality,
  type ContentQualityResult,
} from "@/lib/ist/quality-checks";

const EMPTY_RESULT: ContentQualityResult = {
  wordCount: {
    id: "word_count",
    label: "Word count",
    passed: false,
    count: 0,
    required: 200,
    matches: [],
    severity: "required",
  },
  quantitativeAnchors: {
    id: "quantitative_anchors",
    label: "Quantitative anchors",
    passed: false,
    count: 0,
    required: 3,
    matches: [],
    severity: "required",
  },
  temporalMarkers: {
    id: "temporal_markers",
    label: "Temporal markers",
    passed: false,
    count: 0,
    required: 1,
    matches: [],
    severity: "required",
  },
  namedEntities: {
    id: "named_entities",
    label: "Named entities",
    passed: true,
    count: 0,
    required: 0,
    matches: [],
    severity: "advisory",
  },
  overallReady: false,
};

export function useContentQuality(
  content: string,
  debounceMs = 300
): ContentQualityResult {
  const [result, setResult] = useState<ContentQualityResult>(EMPTY_RESULT);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    if (!content.trim()) {
      setResult(EMPTY_RESULT);
      timerRef.current = null;
    } else {
      timerRef.current = setTimeout(() => {
        setResult(analyzeContentQuality(content));
      }, debounceMs);
    }

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [content, debounceMs]);

  return result;
}
