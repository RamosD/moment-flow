/**
 * Report generation renderer entry point.
 *
 * The real implementation lives in `report-generation.renderer.ts` (CR-601 /
 * CR-602). This barrel keeps the dispatcher import path stable.
 */
export { renderReportGeneration } from './report-generation.renderer';
