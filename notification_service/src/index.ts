import { env } from './config/env';
import { createServer } from './server';
import { bindEmitter } from './modules/realtime/socket.emitter';

function main() {
  const { httpServer, io, pubClient, subClient } = createServer();

  bindEmitter(io);

  httpServer.listen(env.PORT, () => {
    console.log(`notification_service listening on port ${env.PORT} [${env.NODE_ENV}]`);
  });

  process.on('SIGTERM', async () => {
    console.log('shutting_down');
    io.close();
    await pubClient.quit();
    await subClient.quit();
    httpServer.close(() => process.exit(0));
  });
}

main();