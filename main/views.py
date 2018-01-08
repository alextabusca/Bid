from main.forms import ItemForm
from models import Item, Bid
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.db import IntegrityError
from datetime import datetime
from emg.settings import BASE_URL
from django.shortcuts import render

IMAGE_FILE_TYPES = ['png', 'jpg', 'jpeg']

def create_item(request):
    if not request.user.is_authenticated():
        return render(request, 'main/login.html')
    else:
        form = ItemForm(request.POST or None, request.FILES or None)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.image = request.FILES['image']
            item.creator = item.user.username
            file_type = item.image.url.split('.')[-1]
            file_type = file_type.lower()
            if file_type not in IMAGE_FILE_TYPES:
                context = {
                    'item': item,
                    'form': form,
                    'error_message': 'Image file must be PNG, JPG, or JPEG',
                }
                return render(request, 'main/create_item.html', context)
            item.save()

            return redirect(BASE_URL)
        context = {
            "form": form,
        }
        return render(request, 'main/create_item.html', context)


def index(request):
    if 'category' in request.GET:
        category = request.GET['category']
    else:
        category = 'all'
    if 'sort' in request.GET:
        sort = request.GET['sort']
    else:
        sort = 'active'

    if category == 'all':
        item_list = Item.objects.all()
    else:
        item_list = Item.objects.filter(category=category)

    item_list = [item for item in item_list]

    if sort == 'cheapest':
        item_list.sort(key=(lambda item: item.get_current_bid()))
    elif sort == 'priciest':
        item_list.sort(key=(lambda item: -item.get_current_bid()))
    elif sort == 'newest':
        item_list.sort(key=(lambda item: item.start_date))
        item_list.reverse()
    elif sort == 'active':
        item_list.sort(key=(lambda item: item.last_bid_at()))
        item_list.reverse()

    context = {
        'BASE_URL': BASE_URL,
        'category': category,
        'sort': sort,
        'item_list': item_list
    }
    return render(request, 'main/index.html', context)


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        if 'confirm_password' in request.POST:
            confirm_password = request.POST['confirm_password']
            firstname = request.POST['first_name']
            lastname = request.POST['last_name']
            email = request.POST['email']
            if (username == "" or password == "" or password != confirm_password):
                return render(request, 'main/login.html', {'BASE_URL': BASE_URL, 'signup_error': True})
            try:
                User.objects.create_user(username, password=password,
                                         first_name=firstname,
                                         last_name=lastname,
                                         email=email)
            except IntegrityError:
                return render(request, 'main/login.html', {'BASE_URL': BASE_URL, 'already_exists_error': True})
        user = authenticate(username=username, password=password)

        if user is not None and user.is_authenticated():
            login(request, user)
        if user is not None and user.is_authenticated():
            return redirect(BASE_URL + "me")
        else:
            return render(request, 'main/login.html', {'BASE_URL': BASE_URL, 'login_error': True})
    else:
        return render(request, 'main/login.html', {'BASE_URL': BASE_URL, })


def logout_view(request):
    logout(request)
    return redirect(BASE_URL + "me")


def me(request):
    if (request.user.is_authenticated()):

        all_items = Item.objects.all()
        winning_items = []
        beaten_items = []
        for item in all_items:
            try:
                Bid.objects.get(user=request.user, item=item)
            except Bid.DoesNotExist:
                continue
            if item.get_winner() == request.user:
                winning_items.append(item)
            else:
                beaten_items.append(item)
        return render(request, 'main/me.html', {
            'BASE_URL': BASE_URL,
            'winning_items': winning_items,
            'beaten_items': beaten_items
        })
    else:
        return redirect(BASE_URL)


def item(request, id):
    item = Item.objects.get(id=id)
    current_price = item.get_current_bid()
    time_left = item.get_time_left()
    min_bid = 1

    bids_for_item = Bid.objects.filter(item=item).order_by('-price', 'start_date')

    if request.method == 'POST':
        if not time_left:
            return redirect(BASE_URL)  # Not exposed by client

        bid_price = request.POST['bid_price']
        try:
            bid_price = float(bid_price)
        except ValueError:
            return render(request, 'main/item.html',
                          {'BASE_URL': BASE_URL, 'item': item, 'current_price': current_price, 'bid_error': True})

        if bid_price <= current_price + min_bid:
            return render(request, 'main/item.html',
                          {'BASE_URL': BASE_URL, 'item': item, 'current_price': current_price, 'bid_error': True})

        if not request.user.is_authenticated():
            return redirect(BASE_URL)

        try:
            my_bid = Bid.objects.get(user=request.user, item=item)
            my_bid.price = bid_price
            my_bid.start_date = datetime.now()
            my_bid.save()
        except Bid.DoesNotExist:
            my_bid = Bid.objects.create(user=request.user, item=item, price=bid_price)

        current_price = item.get_current_bid()

        return render(request, 'main/item.html', {
            'BASE_URL': BASE_URL,
            'item': item,
            'bids_for_item': bids_for_item,
            'current_price': current_price,
            'bid_success': True,
            'beaten': my_bid.price if item.get_winner() != request.user else False
        })
    else:
        beaten = False
        try:
            my_bid = Bid.objects.get(user=request.user, item=item)
            beaten = my_bid.price
        except:  # Bid.DoesNotExist:
            pass

        winner = None

        if not time_left:
            winner = item.get_winner()

        return render(request, 'main/item.html', {
            'BASE_URL': BASE_URL,
            'item': item,
            'bids_for_item': bids_for_item,
            'current_price': current_price,
            'beaten': beaten if item.get_winner() != request.user else False,
            'winner': winner
        })

def cancel_auction(request, id):
    item = Item.objects.get(id=id)
    item.delete()
    return index(request)
