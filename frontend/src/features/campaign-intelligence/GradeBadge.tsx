import { Badge } from '@/shared/ui'

import { gradeVariant } from './intelligence-format'

/** Overall grade as a colored badge. Neutral "No grade" when absent. */
export function GradeBadge({ grade }: { grade?: string | null }) {
  if (!grade) return <Badge variant="neutral">No grade</Badge>
  return <Badge variant={gradeVariant(grade)}>{grade}</Badge>
}
