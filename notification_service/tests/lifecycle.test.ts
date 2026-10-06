import request from 'supertest';
import { Redis } from 'ioredis';
import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest';

import { createApp } from '../src/app';
import { prisma } from '../src/lib/prisma';
import { pruneSettledBefore } from '../src/modules/notifications/repositories/notificationRepository';
import {
  REALTIME_NOTIFICATION_CHANNEL,
  createRealtimeEventClients,
} from '../src/config/redis';

/**
 * Lifecycle tests for the parts of the inbox that are about *when* a notification
 * exists rather than what it says: dedupe on a repeated create, archiving out of
 * the inbox, the retention prune, and the purge that account deletion depends on.
 *
 * Integration tests against the real Prisma client and dev database, for the same
 * reason as inbox.test.ts: everything that can break here is SQL — `ON CONFLICT
 * DO NOTHING` against the `(user_id, dedupe_key)` index, the `archived_at IS NULL`
 * predicate the list indexes depend on, and the retention cutoff. A mocked
 * repository would pass while the real query plan or constraint fell over.
 *
 * Reuses the same two synthetic ids as inbox.test.ts, which is what keeps the
 * cleanup complete. A row for a third id would leak into the dev inbox on every
 * run.
 */

const SECRET = process.env.GATEWAY_INTERNAL_SECRET as string;

const TEST_USER_ID = 987654321n;
const OTHER_USER_ID = 987654322n;

const app = createApp();

const userHeaders = (userId: bigint = TEST_USER_ID) => ({
  'X-Gateway-Secret': SECRET,
  'X-User-Id': userId.toString(),
});

const internalHeaders = {
  'X-Internal-Secret': SECRET,
  'X-Internal-Service': 'user-service',
};

async function clearTestRows(): Promise<void> {
  await prisma.notification.deleteMany({
    where: { userId: { in: [TEST_USER_ID, OTHER_USER_ID] } },
  });
}

async function seed(overrides: {
  userId?: bigint;
  type?: string;
  title?: string;
  dedupeKey?: string;
  read?: boolean;
  archived?: boolean;
  createdAt?: Date;
} = {}): Promise<string> {
  const created = await prisma.notification.create({
    data: {
      userId: overrides.userId ?? TEST_USER_ID,
      type: overrides.type ?? 'account.register',
      title: overrides.title ?? 'seeded',
      body: '',
      metadata: {},
      dedupeKey: overrides.dedupeKey ?? null,
      readAt: overrides.read ? new Date() : null,
      archivedAt: overrides.archived ? new Date() : null,
      createdAt: overrides.createdAt ?? new Date(),
    },
  });

  return created.id;
}

function createBody(overrides: Record<string, unknown> = {}) {
  return {
    userId: Number(TEST_USER_ID),
    type: 'account.register',
    title: 'created',
    body: 'b',
    ...overrides,
  };
}

beforeAll(async () => {
  await prisma.$connect();
});

afterAll(async () => {
  await clearTestRows();
  await prisma.$disconnect();
});

beforeEach(async () => {
  await clearTestRows();
});

describe('create dedupe', () => {
  it('stores one row and answers 201 for the first call', async () => {
    const res = await request(app)
      .post('/api/v1/notifications/internal/notifications')
      .set(internalHeaders)
      .send(createBody({ dedupeKey: 'account.register:token-1' }));

    expect(res.status).toBe(201);
    expect(res.body.id).toEqual(expect.any(String));
    expect(res.body.read_at).toBeNull();
    expect(res.body.archived_at).toBeNull();
  });

  it('answers 200 with the same id when the same key is replayed', async () => {
    const payload = createBody({ dedupeKey: 'account.register:token-1' });

    const first = await request(app)
      .post('/api/v1/notifications/internal/notifications')
      .set(internalHeaders)
      .send(payload);

    const second = await request(app)
      .post('/api/v1/notifications/internal/notifications')
      .set(internalHeaders)
      .send(payload);

    expect(second.status).toBe(200);
    // Same row, not a new one: a producer retrying after a lost response has to be
    // able to treat the second answer as confirmation of the first.
    expect(second.body.id).toBe(first.body.id);

    const rows = await prisma.notification.count({ where: { userId: TEST_USER_ID } });
    expect(rows).toBe(1);
  });

  it('counts a replayed notification once for the unread badge', async () => {
    const payload = createBody({ dedupeKey: 'account.register:token-1' });

    await request(app)
      .post('/api/v1/notifications/internal/notifications')
      .set(internalHeaders)
      .send(payload);
    await request(app)
      .post('/api/v1/notifications/internal/notifications')
      .set(internalHeaders)
      .send(payload);

    const count = await request(app)
      .get('/api/v1/notify/unread-count')
      .set(userHeaders());

    expect(count.body).toEqual({ unread: 1 });
  });

  it('still inserts separately when no key is supplied', async () => {
    // Backwards compatibility: a producer that has not been updated yet keeps the
    // old every-call-inserts behaviour rather than silently losing notifications.
    for (let i = 0; i < 2; i += 1) {
      const res = await request(app)
        .post('/api/v1/notifications/internal/notifications')
        .set(internalHeaders)
        .send(createBody());

      expect(res.status).toBe(201);
    }

    expect(await prisma.notification.count({ where: { userId: TEST_USER_ID } })).toBe(2);
  });

  it('does not collide across users', async () => {
    // The unique index is (user_id, dedupe_key), not dedupe_key alone: two accounts
    // verifying against the same upstream token id must both get their row.
    const first = await request(app)
      .post('/api/v1/notifications/internal/notifications')
      .set(internalHeaders)
      .send(createBody({ dedupeKey: 'shared-token-id' }));

    const second = await request(app)
      .post('/api/v1/notifications/internal/notifications')
      .set(internalHeaders)
      .send(createBody({ userId: Number(OTHER_USER_ID), dedupeKey: 'shared-token-id' }));

    expect(first.status).toBe(201);
    expect(second.status).toBe(201);
    expect(second.body.id).not.toBe(first.body.id);
  });

  it('allows many rows with no key, since NULLs are distinct in the index', async () => {
    await seed();
    await seed();
    await seed();

    expect(await prisma.notification.count({ where: { userId: TEST_USER_ID } })).toBe(3);
  });

  it('rejects a key longer than the column', async () => {
    const res = await request(app)
      .post('/api/v1/notifications/internal/notifications')
      .set(internalHeaders)
      .send(createBody({ dedupeKey: 'x'.repeat(256) }));

    expect(res.status).toBe(400);
    expect(Object.keys(res.body.details.fieldErrors)).toContain('dedupeKey');
  });

  it('rejects an empty key rather than treating it as absent', async () => {
    // An empty string is a real value that would collapse unrelated notifications
    // onto one row, so it must not pass as "no key".
    const res = await request(app)
      .post('/api/v1/notifications/internal/notifications')
      .set(internalHeaders)
      .send(createBody({ dedupeKey: '   ' }));

    expect(res.status).toBe(400);
  });
});

describe('archive', () => {
  it('takes the row out of the inbox and stamps archived_at', async () => {
    const id = await seed();

    const res = await request(app).post(`/api/v1/notify/${id}/archive`).set(userHeaders());

    expect(res.status).toBe(200);
    expect(res.body.archived_at).not.toBeNull();

    const inbox = await request(app).get('/api/v1/notify/').set(userHeaders());
    expect(inbox.body.count).toBe(0);
  });

  it('does not mark the notification read', async () => {
    // Read and dismissed are different facts. Folding them together would let a
    // dismiss count as "the user saw this" and quietly clear their badge intent.
    const id = await seed();

    const res = await request(app).post(`/api/v1/notify/${id}/archive`).set(userHeaders());

    expect(res.body.read_at).toBeNull();
  });

  it('lists archived rows under ?archived=true', async () => {
    const archivedId = await seed({ title: 'archived' });
    await seed({ title: 'still in inbox' });

    await request(app).post(`/api/v1/notify/${archivedId}/archive`).set(userHeaders());

    const archive = await request(app).get('/api/v1/notify/?archived=true').set(userHeaders());
    expect(archive.body.count).toBe(1);
    expect(archive.body.results[0].title).toBe('archived');

    const inbox = await request(app).get('/api/v1/notify/').set(userHeaders());
    expect(inbox.body.count).toBe(1);
    expect(inbox.body.results[0].title).toBe('still in inbox');
  });

  it('keeps archived=true on the next link', async () => {
    for (let i = 0; i < 3; i += 1) {
      await seed({ archived: true });
    }

    const page = await request(app)
      .get('/api/v1/notify/?archived=true&page_size=2')
      .set(userHeaders());

    expect(page.body.next).toContain('archived=true');
  });

  it('removes an archived unread row from the badge', async () => {
    await seed();
    const archivedId = await seed();

    await request(app).post(`/api/v1/notify/${archivedId}/archive`).set(userHeaders());

    const count = await request(app).get('/api/v1/notify/unread-count').set(userHeaders());
    expect(count.body).toEqual({ unread: 1 });
  });

  it('leaves archived rows out of read-all', async () => {
    await seed();
    const archivedId = await seed();

    await request(app).post(`/api/v1/notify/${archivedId}/archive`).set(userHeaders());

    const res = await request(app).post('/api/v1/notify/read-all').set(userHeaders());
    expect(res.body).toEqual({ updated: 1 });

    const archivedRow = await prisma.notification.findUnique({ where: { id: archivedId } });
    expect(archivedRow?.readAt).toBeNull();
  });

  it('is idempotent and does not move archived_at on a second call', async () => {
    const id = await seed();

    const first = await request(app).post(`/api/v1/notify/${id}/archive`).set(userHeaders());
    const second = await request(app).post(`/api/v1/notify/${id}/archive`).set(userHeaders());

    expect(second.body.archived_at).toBe(first.body.archived_at);
  });

  it('returns 404 for another user notification rather than 403', async () => {
    const id = await seed({ userId: OTHER_USER_ID });

    const res = await request(app).post(`/api/v1/notify/${id}/archive`).set(userHeaders());

    expect(res.status).toBe(404);
  });

  it('rejects a non-uuid id with a 400', async () => {
    const res = await request(app).post('/api/v1/notify/not-a-uuid/archive').set(userHeaders());

    expect(res.status).toBe(400);
  });

  it('accepts archived=true|false and rejects anything else', async () => {
    await expect(
      request(app).get('/api/v1/notify/?archived=true').set(userHeaders()),
    ).resolves.toMatchObject({ status: 200 });

    const res = await request(app).get('/api/v1/notify/?archived=maybe').set(userHeaders());
    expect(res.status).toBe(400);
  });
});

describe('retention prune', () => {
  const DAY = 24 * 60 * 60 * 1000;

  it('deletes read notifications past the cutoff', async () => {
    const stale = await seed({ read: true, createdAt: new Date(Date.now() - 60 * DAY) });

    const deleted = await pruneSettledBefore(new Date(Date.now() - 30 * DAY), 500);

    expect(deleted).toBe(1);
    expect(await prisma.notification.findUnique({ where: { id: stale } })).toBeNull();
  });

  it('keeps unread notifications however old they are', async () => {
    // The user has not dealt with these, so they are still inbox content rather
    // than history. Deleting them would silently drop unread badges' contents.
    const unread = await seed({ read: false, createdAt: new Date(Date.now() - 400 * DAY) });

    const deleted = await pruneSettledBefore(new Date(Date.now() - 30 * DAY), 500);

    expect(deleted).toBe(0);
    expect(await prisma.notification.findUnique({ where: { id: unread } })).not.toBeNull();
  });

  it('keeps recent read notifications', async () => {
    const recent = await seed({ read: true, createdAt: new Date(Date.now() - 2 * DAY) });

    const deleted = await pruneSettledBefore(new Date(Date.now() - 30 * DAY), 500);

    expect(deleted).toBe(0);
    expect(await prisma.notification.findUnique({ where: { id: recent } })).not.toBeNull();
  });

  it('prunes an archived row that was never read', async () => {
    // Dismissed is not read, but the row has served its purpose.
    const dismissed = await seed({ archived: true, createdAt: new Date(Date.now() - 90 * DAY) });

    const deleted = await pruneSettledBefore(new Date(Date.now() - 30 * DAY), 500);

    expect(deleted).toBe(1);
    expect(await prisma.notification.findUnique({ where: { id: dismissed } })).toBeNull();
  });

  it('prunes across every user, not just one', async () => {
    // Deliberately the opposite of the account-deletion purge: retention is a
    // global sweep over rows everyone has already dealt with, and leaving any
    // user's settled rows behind would make the table grow without bound.
    const mine = await seed({ read: true, createdAt: new Date(Date.now() - 90 * DAY) });
    const theirs = await seed({
      userId: OTHER_USER_ID,
      read: true,
      createdAt: new Date(Date.now() - 90 * DAY),
    });

    const deleted = await pruneSettledBefore(new Date(Date.now() - 30 * DAY), 500);

    expect(deleted).toBe(2);
    expect(await prisma.notification.findUnique({ where: { id: mine } })).toBeNull();
    expect(await prisma.notification.findUnique({ where: { id: theirs } })).toBeNull();
  });

  it('deletes in batches rather than one unbounded statement', async () => {
    for (let i = 0; i < 5; i += 1) {
      await seed({ read: true, createdAt: new Date(Date.now() - 60 * DAY) });
    }

    // A batch of 2 must take three passes to clear five rows; the caller loops.
    expect(await pruneSettledBefore(new Date(Date.now() - 30 * DAY), 2)).toBe(2);
    expect(await prisma.notification.count({ where: { readAt: { not: null } } })).toBe(3);
  });
});

describe('account deletion purge', () => {
  it('deletes every row for that user', async () => {
    await seed();
    await seed();

    const res = await request(app)
      .delete(`/api/v1/notifications/internal/users/${TEST_USER_ID}/notifications`)
      .set(internalHeaders);

    expect(res.status).toBe(200);
    expect(res.body).toEqual({ deleted: 2 });
    expect(await prisma.notification.count({ where: { userId: TEST_USER_ID } })).toBe(0);
  });

  it('does not touch another user', async () => {
    await seed({ userId: OTHER_USER_ID });

    await request(app)
      .delete(`/api/v1/notifications/internal/users/${TEST_USER_ID}/notifications`)
      .set(internalHeaders);

    expect(await prisma.notification.count({ where: { userId: OTHER_USER_ID } })).toBe(1);
  });

  it('reports zero for a user with nothing, so a repeat purge is idempotent', async () => {
    const res = await request(app)
      .delete(`/api/v1/notifications/internal/users/${TEST_USER_ID}/notifications`)
      .set(internalHeaders);

    expect(res.body).toEqual({ deleted: 0 });
  });

  it('refuses the purge without the internal secret', async () => {
    await seed();

    const res = await request(app).delete(
      `/api/v1/notifications/internal/users/${TEST_USER_ID}/notifications`,
    );

    expect(res.status).toBe(403);
    expect(await prisma.notification.count({ where: { userId: TEST_USER_ID } })).toBe(1);
  });

  it('rejects a non-numeric user id with a 400', async () => {
    const res = await request(app)
      .delete('/api/v1/notifications/internal/users/abc/notifications')
      .set(internalHeaders);

    expect(res.status).toBe(400);
  });
});

describe('realtime fan-out', () => {
  it('announces a created notification on the Redis channel', async () => {
    // The reason this matters: the socket registry is per-process, so a direct
    // emit only reaches sockets held by the instance that created the row. Every
    // instance subscribes to this channel instead.
    const { subscriber } = createRealtimeEventClients();

    try {
      await subscriber.subscribe(REALTIME_NOTIFICATION_CHANNEL);

      const received = new Promise<{ userId: string; payload: { id: string } }>((resolve) => {
        subscriber.on('message', (channel, message) => {
          if (channel === REALTIME_NOTIFICATION_CHANNEL) {
            resolve(JSON.parse(message));
          }
        });
      });

      const res = await request(app)
        .post('/api/v1/notifications/internal/notifications')
        .set(internalHeaders)
        .send(createBody({ dedupeKey: 'realtime-1' }));

      const event = await Promise.race([
        received,
        new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error('no realtime message within 5s')), 5000),
        ),
      ]);

      expect(event.userId).toBe(String(TEST_USER_ID));
      expect(event.payload.id).toBe(res.body.id);
    } finally {
      await subscriber.quit();
    }
  });

  it('does not announce a deduplicated replay', async () => {
    const { subscriber } = createRealtimeEventClients();

    try {
      await subscriber.subscribe(REALTIME_NOTIFICATION_CHANNEL);

      const messages: string[] = [];
      subscriber.on('message', (channel, message) => {
        if (channel === REALTIME_NOTIFICATION_CHANNEL) messages.push(message);
      });

      const payload = createBody({ dedupeKey: 'realtime-2' });
      await request(app)
        .post('/api/v1/notifications/internal/notifications')
        .set(internalHeaders)
        .send(payload);
      await request(app)
        .post('/api/v1/notifications/internal/notifications')
        .set(internalHeaders)
        .send(payload);

      // Give a stray second publish time to arrive before asserting it did not.
      await new Promise((resolve) => setTimeout(resolve, 500));

      expect(messages).toHaveLength(1);
    } finally {
      await subscriber.quit();
    }
  });
});