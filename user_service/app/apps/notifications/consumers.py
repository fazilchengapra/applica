from channels.generic.websocket import AsyncJsonWebsocketConsumer


class NotificationConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        user = self.scope["user"]

        if user.is_anonymous:
            await self.close()
            return
        # adding group_name -> user_{id}
        self.group_name = f"user_{user.id}"

        await self.channel_layer.group_add(
            self.group_name,

            # channel_name is unique id for each tab
            self.channel_name,
        )

        # connection accept now receive notifications
        await self.accept()

    # disconnect the web_socket hand_shake
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name,
        )

    # function for send notification -> call business logic using type name
    async def send_notification(self, event):
        await self.send_json(event["data"])

    async def cv_status_update(self, event):
            await self.send_json(event["data"])