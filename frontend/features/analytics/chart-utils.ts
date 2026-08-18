export function clamp01(value: number) {
  return Math.max(0, Math.min(1, value));
}

export function percent(value: number, digits = 0) {
  return `${(clamp01(value) * 100).toFixed(digits)}%`;
}

export function svgPoint(
  index: number,
  total: number,
  value: number,
  width: number,
  height: number,
  padX: number,
  padY: number,
) {
  const denominator = Math.max(1, total - 1);
  return {
    x: padX + (index / denominator) * (width - padX * 2),
    y: padY + (1 - clamp01(value)) * (height - padY * 2),
  };
}
