/**
 * Content generation renderer entry point.
 *
 * The real implementation lives in `content-generation.renderer.ts` (CR-501 /
 * CR-502 / CR-802). This barrel keeps the dispatcher import path stable.
 */
export { renderContentGeneration } from './content-generation.renderer';
