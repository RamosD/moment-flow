/**
 * Tiny className combiner — avoids pulling in `clsx` for a one-liner.
 * Falsy values are skipped so conditional classes read cleanly.
 */
export type ClassValue = string | number | false | null | undefined

export function cx(...values: ClassValue[]): string {
  return values.filter(Boolean).join(' ')
}
