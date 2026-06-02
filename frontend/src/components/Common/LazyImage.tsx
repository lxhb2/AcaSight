import React from 'react';
import { useLazyImage } from '@/hooks/useLazyImage';

interface LazyImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  src: string;
  rootMargin?: string;
  placeholderSrc?: string;
}

export const LazyImage: React.FC<LazyImageProps> = ({
  src,
  rootMargin,
  placeholderSrc,
  onLoad,
  style,
  ...rest
}) => {
  const { ref, src: currentSrc, isLoaded, onLoad: handleLazyLoad } = useLazyImage(src, {
    rootMargin,
    placeholderSrc,
  });

  const combinedOnLoad = React.useCallback((e: React.SyntheticEvent<HTMLImageElement>) => {
    handleLazyLoad();
    onLoad?.(e);
  }, [handleLazyLoad, onLoad]);

  return (
    <img
      ref={ref}
      src={currentSrc}
      onLoad={combinedOnLoad}
      style={{
        ...style,
        opacity: isLoaded ? 1 : 0.5,
        transition: 'opacity 0.3s ease',
      }}
      {...rest}
    />
  );
};
