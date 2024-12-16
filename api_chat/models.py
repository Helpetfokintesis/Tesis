from django.db import models


class api_chat_message(models.Model):
        user_message = models.TextField()
        bot_message = models.TextField()    
        timestamp = models.DateTimeField(auto_now_add=True)
