from django.db import models
from django.contrib.auth.models import User
from datetime import datetime
from django.core.validators import MinValueValidator

# new choices (inspired from liveauctioneers.com)
CATEGORY_CHOICES = (
    ('all', 'All'),
    ('art', 'Art'),
    ('jewelry', 'Jewelry'),
    ('antiques', 'Antiques'),
    ('furniture', 'Furniture'),
    ('collectibles', 'Collectibles'),
    ('home&garden', 'Home & Garden'),
    ('fashion', 'Fashion'),
)

class Item(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=600)
    image = models.FileField(upload_to='images/')
    initial_price = models.DecimalField(default=0, max_digits=6, decimal_places=2,
                                        validators=[
                                            MinValueValidator(0.0, message="Initial price must be greater than 0!")])
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES, default='all')
    start_date = models.DateTimeField(default=datetime.now, blank=True)
    end_date = models.DateTimeField()
    # asta ii ca sa vedem daca un user care pune bid ii creatoru licitatiei sau ba
    creator = models.CharField(max_length=191, null=True)

    def last_bid_at(self):
        bids = Bid.objects.filter(item=self).order_by('-start_date')
        if not bids:
            return self.start_date
        else:
            return bids[0].start_date

    def get_current_bid(self):
        bids = Bid.objects.filter(item=self).order_by('-price', 'start_date')
        if len(bids) == 0:
            return self.initial_price
        else:
            return bids[0].price

    def get_winner(self):
        bids = Bid.objects.filter(item=self).order_by('-price', 'start_date')
        if bids:
            return bids[0].user
        else:
            return None

    def get_time_left(self):
        now = datetime.now()
        naive = self.end_date.replace(tzinfo=None)
        delta = naive - now
        ts = int(delta.total_seconds())
        if ts <= 0:
            return ""
        else:
            days = int(ts / 86400)
            hours = int((ts % 86400) / 3600)
            minutes = int((ts % 3600) / 60)
            seconds = int((ts % 60) / 1)
            arr = [days, hours, minutes, seconds]
            letters = "dhms"
            anything = False
            output = ""
            for i in xrange(4):
                if arr[i]: anything = True
                if anything:
                    output += (str(arr[i]) + letters[i] + " ")
            return output[:-1]


class Bid(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    user = models.ForeignKey(User)
    price = models.DecimalField(default=0, max_digits=8, decimal_places=2)
    start_date = models.DateTimeField(default=datetime.now, blank=True)
