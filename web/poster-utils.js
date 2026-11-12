// Only TMDB file paths are accepted, never arbitrary image URLs from cinema pages.
export function posterURL(path) {
  return typeof path==='string' && /^\/[a-zA-Z0-9_-]+\.(jpg|png|webp)$/.test(path)
    ? 'https://image.tmdb.org/t/p/w185'+path : null;
}
