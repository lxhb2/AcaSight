import { useState, useCallback, useRef, useEffect } from 'react';

interface UseLazyImageOptions {
  rootMargin?: string;
  threshold?: number;
  placeholderSrc?: string;
}

export function useLazyImage(src: string, options: UseLazyImageOptions = {}) {
  const { rootMargin = '200px', threshold = 0.01, placeholderSrc = '' } = options;
  const [isLoaded, setIsLoaded] = useState(false);
  const [isInView, setIsInView] = useState(false);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);

  const setRef = useCallback(
    (node: HTMLImageElement | null) => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }

      imgRef.current = node;

      if (!node) return;

      observerRef.current = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) {
            setIsInView(true);
            observerRef.current?.disconnect();
          }
        },
        { rootMargin, threshold },
      );

      observerRef.current.observe(node);
    },
    [rootMargin, threshold],
  );

  useEffect(() => {
    return () => {
      observerRef.current?.disconnect();
    };
  }, []);

  const handleLoad = useCallback(() => {
    setIsLoaded(true);
  }, []);

  const currentSrc = isInView ? src : placeholderSrc;

  return { ref: setRef, src: currentSrc, isLoaded, isInView, onLoad: handleLoad };
}
