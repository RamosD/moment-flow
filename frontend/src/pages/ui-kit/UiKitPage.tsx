import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  Section,
  Skeleton,
} from '@/shared/ui'
import {
  ForbiddenError,
  NetworkError,
  NotFoundError,
  ServiceUnavailableError,
  UnauthorizedError,
} from '@/shared/api'

import styles from './UiKitPage.module.css'

const BUTTON_VARIANTS = [
  'primary',
  'secondary',
  'ghost',
  'neutral',
  'danger',
  'success',
  'warning',
] as const

const BADGE_VARIANTS = [
  'neutral',
  'primary',
  'success',
  'warning',
  'danger',
  'info',
] as const

/**
 * Internal living style guide for the shared UI primitives and transversal
 * states. Not linked in the main navigation; reachable at /ui-kit for visual
 * validation during development.
 */
export function UiKitPage() {
  return (
    <>
      <PageHeader
        title="UI Kit"
        description="Living reference for shared/ui primitives and transversal states."
        actions={<Button>Primary action</Button>}
      />

      <Section title="Buttons" description="Variants and states.">
        <div className={styles.row}>
          {BUTTON_VARIANTS.map((variant) => (
            <Button key={variant} variant={variant}>
              {variant}
            </Button>
          ))}
        </div>
        <div className={styles.row}>
          <Button size="sm">Small</Button>
          <Button size="md">Medium</Button>
          <Button disabled>Disabled</Button>
        </div>
      </Section>

      <Section title="Badges">
        <div className={styles.row}>
          {BADGE_VARIANTS.map((variant) => (
            <Badge key={variant} variant={variant}>
              {variant}
            </Badge>
          ))}
        </div>
      </Section>

      <Section title="Cards & Skeleton">
        <div className={styles.grid}>
          <Card>
            <h3>Card title</h3>
            <p>Neutral surface container for grouping content.</p>
          </Card>
          <Card>
            <div className={styles.stack}>
              <Skeleton width="60%" height="1.2rem" />
              <Skeleton />
              <Skeleton width="80%" />
            </div>
          </Card>
        </div>
      </Section>

      <Section title="Alerts">
        <div className={styles.stack}>
          <Alert variant="info" title="Info">
            Informational message.
          </Alert>
          <Alert variant="success" title="Success">
            Operation completed.
          </Alert>
          <Alert variant="warning" title="Warning">
            Something needs attention.
          </Alert>
          <Alert variant="danger" title="Danger">
            Something failed.
          </Alert>
        </div>
      </Section>

      <Section title="States" description="loading / empty / error patterns.">
        <div className={styles.grid}>
          <div className={styles.bordered}>
            <LoadingState label="Loading campaign…" />
          </div>
          <div className={styles.bordered}>
            <EmptyState
              title="No campaigns yet"
              description="Create your first campaign to get started."
              action={<Button size="sm">New campaign</Button>}
            />
          </div>
        </div>
      </Section>

      <Section
        title="Error patterns"
        description="Derived from API error types (network / 401 / 403 / 404 / 503)."
      >
        <div className={styles.grid}>
          <div className={styles.bordered}>
            <ErrorState
              error={new NetworkError('failed')}
              onRetry={() => undefined}
            />
          </div>
          <div className={styles.bordered}>
            <ErrorState error={new UnauthorizedError('expired', {})} />
          </div>
          <div className={styles.bordered}>
            <ErrorState error={new ForbiddenError('denied', {})} />
          </div>
          <div className={styles.bordered}>
            <ErrorState error={new NotFoundError('missing', {})} />
          </div>
          <div className={styles.bordered}>
            <ErrorState
              error={new ServiceUnavailableError('down', { status: 503 })}
              onRetry={() => undefined}
            />
          </div>
        </div>
      </Section>
    </>
  )
}
