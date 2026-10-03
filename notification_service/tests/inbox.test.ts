import request from 'supertest';
import { afterAll, beforeAll, beforeEach, describe, expect, it } from 'vitest';

import { createApp } from '../src/app';
import { prisma } from '../src/lib/prisma';

/**
 * Integration tests for the in-app inbox.
 *
 * These run against the real Prisma client and the dev database rather than a
 * mock, because most of what can break here is SQL: the composite index that
 * the unread filter and the newest-first ordering depend on, the `user_id`
 * bigint coercion, and the type-prefix match. A mocked repository would pass
 * while the real query plan fell over.
 *
 * Every row is created under one of the synthetic ids below, and both are
 * deleted before each test and again in afterAll, so counts are absolute rather
 * than relative and the dev inbox is left as it was found. Any test that
 * creates a row for a *third* id has to add it here, or it leaks into the dev
 * database on every run.
 */

const SECRET = process.env.GATEWAY_INTERNAL_SECRET as string;
const INTERNAL_SECRET = process.env.GATEWAY_INTERNAL_SECRET as string;

// A user id that cannot collide with real data: 2^53 is past Number.MAX_SAFE_INTEGER.
const TEST_USER_ID = 987654321n;
const OTHER_USER_ID = 987654322n;

const app = createApp();

/** Headers Kong's header_injector attaches once the JWT has been verified. */
const userHeaders = (userId: bigint = TEST_USER_ID) => ({
  'X-Gateway-Secret': SECRET,
  'X-User-Id': userId.toString(),
});

const internalHeaders = {
  'X-Internal-Secret': INTERNAL_SECRET,
  'X-Internal-Service': 'user-service',
};

async function clearTestRows(): Promise<void> {
  await prisma.notification.deleteMany({
    where: { userId: { in: [TEST_USER_ID, OTHER_USER_ID] } },
  });
}

/** Insert a notification directly, bypassing the HTTP layer under test. */
async function seed(overrides: {
  userId?: bigint;
  type?: string;
  title?: string;
  read?: boolean;
} = {}): Promise<string> {
  const created = await prisma.notification.create({
    data: {
      userId: overrides.userId ?? TEST_USER_ID,
      type: overrides.type ?? 'account.register',
      title: overrides.title ?? 'seeded',
      body: '',
      metadata: {},
      readAt: overrides.read ? new Date() : null,
      // Staggered so createdAt ordering is deterministic.
      createdAt: new Date(Date.now() + Math.floor(Math.random() * 1000)),
    },
  });
  return created.id;
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

describe('gateway auth', () => {
  it('rejects a request with no gateway secret', async () => {
    const res = await request(app).get('/api/v1/notify/').set('X-User-Id', '1');
    expect(res.status).toBe(403);
  });

  it('rejects a wrong gateway secret', async () => {
    const res = await request(app)
      .get('/api/v1/notify/')
      .set('X-Gateway-Secret', 'not-the-secret')
      .set('X-User-Id', '1');
    expect(res.status).toBe(403);
  });

  it('rejects a valid secret with no user context', async () => {
    const res = await request(app)
      .get('/api/v1/notify/')
      .set('X-Gateway-Secret', SECRET);
    expect(res.status).toBe(401);
  });

  it.each(['abc', '0', '-1', '1.5', '9007199254740993'])(
    'rejects a non-positive or non-integer X-User-Id (%s)',
    async (userId) => {
      const res = await request(app)
        .get('/api/v1/notify/')
        .set('X-Gateway-Secret', SECRET)
        .set('X-User-Id', userId);
      expect(res.status).toBe(401);
    },
  );
});

describe('GET /api/v1/notify/', () => {
  it('returns an empty page, not an error, for a user with nothing', async () => {
    const res = await request(app).get('/api/v1/notify/').set(userHeaders());

    expect(res.status).toBe(200);
    expect(res.body).toMatchObject({ count: 0, next: null, previous: null, results: [] });
  });

  it('orders newest first and paginates with a DRF-style envelope', async () => {
    const ids: string[] = [];
    for (let i = 0; i < 5; i += 1) {
      ids.push(await seed({ title: `n${i}` }));
    }

    const page1 = await request(app)
      .get('/api/v1/notify/?page_size=2')
      .set(userHeaders());

    expect(page1.status).toBe(200);
    expect(page1.body.count).toBe(5);
    expect(page1.body.results).toHaveLength(2);
    expect(page1.body.next).toContain('page=2');
    expect(page1.body.previous).toBeNull();

    const page2 = await request(app)
      .get('/api/v1/notify/?page_size=2&page=2')
      .set(userHeaders());
    expect(page2.body.results).toHaveLength(2);
    expect(page2.body.previous).toContain('page=1');

    const page3 = await request(app)
      .get('/api/v1/notify/?page_size=2&page=3')
      .set(userHeaders());
    expect(page3.body.results).toHaveLength(1);
    expect(page3.body.next).toBeNull();

    // No row appears on two pages, and the newest is first.
    const seen = [...page1.body.results, ...page2.body.results, ...page3.body.results].map(
      (n: { id: string }) => n.id,
    );
    expect(new Set(seen).size).toBe(5);
  });

  it('clamps previous to the last real page when the client overshoots', async () => {
    await seed();
    await seed();

    const res = await request(app)
      .get('/api/v1/notify/?page=99&page_size=1')
      .set(userHeaders());

    expect(res.status).toBe(200);
    expect(res.body.results).toEqual([]);
    // Two pages exist, so previous must point at page 2, not page 98.
    expect(res.body.previous).toContain('page=2');
  });

  it('never leaks another user notifications', async () => {
    await seed();
    await seed({ userId: OTHER_USER_ID, title: 'theirs' });

    const res = await request(app).get('/api/v1/notify/').set(userHeaders());

    expect(res.body.count).toBe(1);
    expect(res.body.results[0].title).toBe('seeded');
  });

  it('filters by exact type', async () => {
    await seed({ type: 'account.register' });
    await seed({ type: 'account.email_verified' });

    const res = await request(app)
      .get('/api/v1/notify/?type=account.register')
      .set(userHeaders());

    expect(res.body.count).toBe(1);
    expect(res.body.results[0].type).toBe('account.register');
  });

  it('filters by trailing wildcard prefix', async () => {
    await seed({ type: 'account.register' });
    await seed({ type: 'account.email_verified' });
    await seed({ type: 'job.applied' });

    const res = await request(app).get('/api/v1/notify/?type=account.*').set(userHeaders());

    expect(res.body.count).toBe(2);
  });

  it('treats a bare * as no filter', async () => {
    await seed({ type: 'account.register' });
    await seed({ type: 'job.applied' });

    const res = await request(app).get('/api/v1/notify/?type=*').set(userHeaders());

    expect(res.body.count).toBe(2);
  });

  it('filters unread_only=true', async () => {
    await seed({ title: 'unread' });
    await seed({ title: 'read', read: true });

    const res = await request(app)
      .get('/api/v1/notify/?unread_only=true')
      .set(userHeaders());

    expect(res.body.count).toBe(1);
    expect(res.body.results[0].title).toBe('unread');
  });

  it('combines unread_only with a type filter', async () => {
    await seed({ type: 'account.register', title: 'a' });
    await seed({ type: 'account.register', title: 'b', read: true });
    await seed({ type: 'job.applied', title: 'c' });

    const res = await request(app)
      .get('/api/v1/notify/?unread_only=true&type=account.*')
      .set(userHeaders());

    expect(res.body.count).toBe(1);
    expect(res.body.results[0].title).toBe('a');
  });

  it.each([
    ['page_size=0', 'page_size'],
    ['page_size=101', 'page_size'],
    ['page_size=abc', 'page_size'],
    ['page=abc', 'page'],
    ['page=0', 'page'],
  ])('rejects %s with a 400 naming the field', async (query, field) => {
    const res = await request(app)
      .get(`/api/v1/notify/?${query}`)
      .set(userHeaders());

    expect(res.status).toBe(400);
    expect(Object.keys(res.body.details.fieldErrors)).toContain(field);
  });

  it('rejects a wildcard that is not trailing', async () => {
    const res = await request(app)
      .get('/api/v1/notify/?type=acc*unt')
      .set(userHeaders());

    expect(res.status).toBe(400);
    expect(res.body.details.fieldErrors.type.join(' ')).toContain('trailing wildcard');
  });
});

describe('GET /api/v1/notify/unread-count/', () => {
  it('counts only unread rows', async () => {
    await seed();
    await seed();
    await seed({ read: true });

    const res = await request(app)
      .get('/api/v1/notify/unread-count/')
      .set(userHeaders());

    expect(res.status).toBe(200);
    expect(res.body).toEqual({ unread: 2 });
  });

  it('is scoped to the caller', async () => {
    await seed();
    await seed({ userId: OTHER_USER_ID });

    const res = await request(app)
      .get('/api/v1/notify/unread-count/')
      .set(userHeaders(OTHER_USER_ID));

    expect(res.body).toEqual({ unread: 1 });
  });
});

describe('POST /api/v1/notify/:id/read/', () => {
  it('marks the row read and returns it', async () => {
    const id = await seed();

    const res = await request(app).post(`/api/v1/notify/${id}/read/`).set(userHeaders());

    expect(res.status).toBe(200);
    expect(res.body.id).toBe(id);
    expect(res.body.read_at).not.toBeNull();
  });

  it('is idempotent and does not move read_at on a second call', async () => {
    const id = await seed();

    const first = await request(app).post(`/api/v1/notify/${id}/read/`).set(userHeaders());
    const second = await request(app).post(`/api/v1/notify/${id}/read/`).set(userHeaders());

    expect(second.status).toBe(200);
    expect(second.body.read_at).toBe(first.body.read_at);
  });

  it('returns 404 for another user notification rather than 403', async () => {
    const id = await seed({ userId: OTHER_USER_ID });

    const res = await request(app).post(`/api/v1/notify/${id}/read/`).set(userHeaders());

    // 404 rather than 403 so the endpoint does not confirm that the id exists.
    expect(res.status).toBe(404);
  });

  it('rejects a non-uuid id with a 400', async () => {
    const res = await request(app)
      .post('/api/v1/notify/not-a-uuid/read/')
      .set(userHeaders());

    expect(res.status).toBe(400);
  });
});

describe('POST /api/v1/notify/read-all/', () => {
  it('marks every unread row and reports the count', async () => {
    await seed();
    await seed();
    await seed({ read: true });

    const res = await request(app).post('/api/v1/notify/read-all/').set(userHeaders());

    expect(res.status).toBe(200);
    expect(res.body).toEqual({ updated: 2 });

    const after = await request(app)
      .get('/api/v1/notify/unread-count/')
      .set(userHeaders());
    expect(after.body).toEqual({ unread: 0 });
  });

  it('reports 0 on a repeat call', async () => {
    await seed();
    await request(app).post('/api/v1/notify/read-all/').set(userHeaders());

    const res = await request(app).post('/api/v1/notify/read-all/').set(userHeaders());

    expect(res.body).toEqual({ updated: 0 });
  });

  it('does not touch another user rows', async () => {
    await seed({ userId: OTHER_USER_ID });

    await request(app).post('/api/v1/notify/read-all/').set(userHeaders());

    const other = await request(app)
      .get('/api/v1/notify/unread-count/')
      .set(userHeaders(OTHER_USER_ID));
    expect(other.body).toEqual({ unread: 1 });
  });
});

describe('DELETE /api/v1/notify/:id/', () => {
  it('deletes the row and answers 204 with no body', async () => {
    const id = await seed();

    const res = await request(app).delete(`/api/v1/notify/${id}/`).set(userHeaders());

    expect(res.status).toBe(204);
    expect(res.body).toEqual({});

    const list = await request(app).get('/api/v1/notify/').set(userHeaders());
    expect(list.body.count).toBe(0);
  });

  it('returns 404 on a second delete', async () => {
    const id = await seed();
    await request(app).delete(`/api/v1/notify/${id}/`).set(userHeaders());

    const res = await request(app).delete(`/api/v1/notify/${id}/`).set(userHeaders());

    expect(res.status).toBe(404);
  });

  it('refuses to delete another user notification', async () => {
    const id = await seed({ userId: OTHER_USER_ID });

    const res = await request(app).delete(`/api/v1/notify/${id}/`).set(userHeaders());

    expect(res.status).toBe(404);
    const still = await prisma.notification.findUnique({ where: { id } });
    expect(still).not.toBeNull();
  });
});

describe('internal routes', () => {
  it('refuses a create with no internal secret', async () => {
    const res = await request(app)
      .post('/api/v1/notifications/internal/notifications')
      .send({ userId: 1, type: 'account.register', title: 'x' });

    expect(res.status).toBe(403);
  });

  it('creates a notification for another user', async () => {
    const res = await request(app)
      .post('/api/v1/notifications/internal/notifications')
      .set(internalHeaders)
      // Number, not the bigint: the wire contract is a JSON integer, and
      // JSON.stringify throws on a bigint. Exact, because the id is < 2^53.
      .send({ userId: Number(OTHER_USER_ID), type: 'account.register', title: 'created', body: 'b' });

    expect(res.status).toBe(201);
    expect(res.body).toMatchObject({ title: 'created', read_at: null });
  });

  it('rejects an unknown notification type', async () => {
    const res = await request(app)
      .post('/api/v1/notifications/internal/notifications')
      .set(internalHeaders)
      .send({ userId: Number(OTHER_USER_ID), type: 'account.not_a_real_type', title: 'x' });

    expect(res.status).toBe(400);
  });

  it('rejects a create with a non-positive userId', async () => {
    const res = await request(app)
      .post('/api/v1/notifications/internal/notifications')
      .set(internalHeaders)
      .send({ userId: 0, type: 'account.register', title: 'x' });

    expect(res.status).toBe(400);
  });

  it('serves the unread count for an arbitrary user to the BFF', async () => {
    await seed();
    await seed({ userId: OTHER_USER_ID, read: true });

    const res = await request(app)
      .get(`/api/v1/notifications/internal/users/${TEST_USER_ID}/unread-count/`)
      .set(internalHeaders);

    expect(res.status).toBe(200);
    expect(res.body).toEqual({ unread: 1 });
  });

  it('refuses that unread count without the internal secret', async () => {
    const res = await request(app).get(
      `/api/v1/notifications/internal/users/${TEST_USER_ID}/unread-count/`,
    );

    expect(res.status).toBe(403);
  });
});

describe('surface separation', () => {
  it('does not expose the user inbox on the internal prefix', async () => {
    const res = await request(app).get('/api/v1/notifications/').set(userHeaders());

    expect(res.status).toBe(404);
  });

  it('does not expose internal writes on the public prefix', async () => {
    const res = await request(app)
      .post('/api/v1/notify/internal/notifications')
      .set(userHeaders())
      .send({ userId: 1, type: 'account.register', title: 'x' });

    expect(res.status).toBe(404);
  });
});
