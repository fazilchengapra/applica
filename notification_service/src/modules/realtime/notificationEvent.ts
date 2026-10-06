import {
  REALTIME_NOTIFICATION_CHANNEL,
  createRealtimeEventClients,
} from '../../config/redis';

const { publisher } = createRealtimeEventClients();

export async function publishNotificationCreated(
  userId: string,
  payload: unknown,
): Promise<void> {
  await publisher.publish(
    REALTIME_NOTIFICATION_CHANNEL,
    JSON.stringify({ userId, payload }),
  );
}