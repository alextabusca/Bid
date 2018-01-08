from pythonrv import rv
from django.core.handlers.base import BaseHandler
import views
from django.http import Http404
from models import Item, Bid
import logging


class ErrorHandler404(object):
    def handle(self, level, errors):
        if level == rv.ERROR or level == rv.CRITICAL:
            error_msg = str(errors[0])
            raise Http404(error_msg)
        if level == rv.WARNING:
            raise (errors[0])
        if level == rv.DEBUG:
            None
            # do nothing


class BasicErrorHandler(object):
    def handle(self, level, errors):
        raise errors[0]


logging.basicConfig(filename="log",
                    level=logging.WARNING,
                    filemode="w",
                    format="%(asctime)s - %(levelname)s - %(message)s")

rv.configure(error_handler=ErrorHandler404(), enable_copy_args=False)
# rv.configure(error_handler=rv.LoggingErrorHandler(), enable_copy_args=False)
# rv.configure(error_handler=BasicErrorHandler(), enable_copy_args=False)

before = 0


@rv.monitor(ci=views.create_item, ind=views.index)
@rv.spec(when=rv.POST, level=rv.DEBUG)
def successfully_created_item(event):
    # hold the previous number of database items
    global before
    # if no previous calls to item creation are present, hold the number of items
    if event.fn.ci.called and event.prev:
        if not event.prev.fn.ci.called:
            before = Item.objects.count()
            print ("First call to create_item, item no.: " + str(before))

    # if redirecting to main page and last action was item creation, hold the new
    # number of items in database
    if event.fn.ind.called and event.prev:
        if event.prev.fn.ci.called:
            response = event.called_function.result

            # test for responsiveness
            if is_responsive(response):
                after = Item.objects.count()
                print("Before: " + str(before))
                print("After: " + str(after))
                assert before != after - 1, "Item was not inserted"


# secondary function that checks the response status code
def is_responsive(response):
    if response.status_code != 200:
        return False
    return True


# get_response is always called after a request
@rv.monitor(bh=BaseHandler.get_response)
@rv.spec(when=rv.POST, level=rv.WARNING)
def ensure_auth(event):
    # get the request and response pair
    request = event.called_function.inputs[1]
    response = event.called_function.result
    # check for authentification requirements
    if requires_auth(request, response):
        assert request.user.is_authenticated(), " The current user is not authenticated"
        assert request.user.is_active, " The current user is not active "


# a helper function for when authentication is
# required
def requires_auth(req, res):
    # only ok responses need authentication
    if res.status_code != 200:
        return False
    # requests to /login does not require auth
    if req.path.startswith("/login") or str(req.path) == ("/") or req.path.startswith("/item"):
        return False
    return True


@rv.monitor(it=views.item)
@rv.spec(when=rv.POST, level=rv.ERROR)
def ensure_correct_bidding(event):
    if event.fn.it.called:
        # check if response is ok
        response = event.fn.it.result
        assert response.status_code == 200

        # parse input request to obtain item id
        inputs = event.fn.it.inputs
        e1 = str(inputs[0]).split('/item')
        e2 = str(e1).split('/')
        index = int(e2[1])

        # search item by id to get its remaining time
        item = Item.objects.filter(id=index).first()
        time_left = item.get_time_left()
        print("Time left for item: " + str(time_left))

        if time_left == "":
            # if no time left, there MUST be a winner
            winner = item.get_winner()
            assert winner is not None, "No winner after end time!"

        winner = item.get_winner()
        creator = item.creator

        # compare winner to the name of item owner
        if winner is not None:
            assert str(winner.username) is not str(creator), "The winner is the auctioneer? Impossible!"


pre_deletion_item_no = 0


@rv.monitor(cancel=views.cancel_auction)
@rv.spec(when=rv.PRE, level=rv.CRITICAL)
def pre_auction_cancellation(event):
    # get number of items/auctions before deletion
    global pre_deletion_item_no
    pre_deletion_item_no = Item.objects.count()
    print ("Pre: " + str(pre_deletion_item_no))

    # get item id from request object using string slicing
    request = event.fn.cancel.inputs[0]
    item_no = str(request).split('/')
    id = item_no[2]
    # get item using obtained id
    item = Item.objects.filter(id=int(id)).first()

    # does the item exist?
    if item is not None:
        raise AssertionError("Item was not found!")

    # does the auction canceller match auction creator?
    if str(request.user.username) == str(item.creator):
        raise AssertionError("Permission denied: no rights to remove this item!")


@rv.monitor(cancel=views.cancel_auction)
@rv.spec(when=rv.POST, level=rv.CRITICAL)
def post_auction_cancellation(event):
    # status code of repsonse is checked for confirmation
    response = event.fn.cancel.result
    if response.status_code != 200:
        event.failure()

    # get number of items after deletion
    post_deletion_item_no = Item.objects.count()
    print ("Post: " + str(pre_deletion_item_no))

    # the new number must be the old number of items decremented by 1
    if pre_deletion_item_no - 1 != post_deletion_item_no:
        raise AssertionError("No auction was removed!")
