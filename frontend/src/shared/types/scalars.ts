/**
 * Primitive aliases that mirror OpenAPI `format` hints. They document intent
 * (these are not arbitrary strings) without adding runtime cost.
 */

/** String in UUID format (OpenAPI `format: uuid`). */
export type UUID = string

/** ISO-8601 calendar date, `YYYY-MM-DD` (OpenAPI `format: date`). */
export type ISODateString = string

/** ISO-8601 date-time (OpenAPI `format: date-time`). */
export type ISODateTimeString = string

/** Free-form metadata bag (`metadata: {}` in the schema). */
export type Metadata = Record<string, unknown>
