# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
import logging
import ask_sdk_core.utils as ask_utils

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response

from functools import cmp_to_key
from datetime import datetime, timedelta

#firebase initialization
import firebase_admin
import asyncio
import json
# import time 
from firebase_admin import credentials, firestore

# cred = credentials.Certificate("firebase.json")
cred = credentials.Certificate("firestoreDB.json")
firebase_admin.initialize_app(cred)

db = firestore.client()


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# return a sorted list of tasks
def dictionaryToList(docs):
    x = []
    for doc in docs:
        task_name = doc.id
        info = doc.to_dict()
        sub_x = [info['task'], info['deadline_time'], info['deadline_date'], info['priority']]
        x.append(sub_x)
    x.sort(key = cmp_to_key(compare))
    return x

#Comparator for sort
def compare(i1,i2):
    date1 = i1[2].split("-")
    date2 = i2[2].split("-")
    for i in range(3):
        if date1[i] != date2[i]:
            return int(date1[i])-int(date2[i])
    time1 = i1[1].split(":")
    time2 = i2[1].split(":")
    for i in range(2):
        if time1[i] != time2[i]:
            return int(time1[i])-int(time2[i])
    return int(i2[3])-int(i1[3])

# insert an item and sort list
def insert_items(task, time, date, priority, items):
    # global items
    
    items.append([task,time,date,priority])
    items.sort(key = cmp_to_key(compare))

#covernt time to xxx am/pm
def time_convert(time):
    time_comps = str(time).split(":")
    hour = int(time_comps[0])
    minute = int(time_comps[1])
    if hour == 0:
        hour_result = "12"
        period = "a. m."
    elif hour < 12:
        hour_result = str(hour)
        period = "a. m."
    elif hour == 12:
        hour_result = "12"
        period = "p. m."
    else:
        hour_result = str(hour-12)
        period = "p. m."
        
    if minute ==0:
        minute_res = ""
    else:
        minute_res = str(minute)+" "
    res = hour_result +" "+ minute_res + period
    return res

# items = [["clean room",["2022","December","1"],3],["review exam",["2022","December","3"],6]]
# docs = db.collection(u'priority_planner').stream()
# items = dictionaryToList(docs)
user_id = None
items = None
cur_read_idx = 0
# items = [["clean room","00:00","2022-12-02","3"],["review exam","13:30","2022-12-04","6"]]

class SkillEventHandler(AbstractRequestHandler):
    """Handler for Skill_Enabled or Skill_Disabled."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("AlexaSkillEvent.SkillEnabled") or ask_utils.is_request_type("AlexaSkillEvent.SkillDisabled")
    def handle(self, handler_input):
        global user_id
        
        # get skill event type
        event_type = handler_input.request_envelope.request.object_type
        # get user id -> collection name
        user_id = handler_input.request_envelope.context.system.user.user_id
        
        if event_type == "AlexaSkillEvent.SkillDisabled":
            # delete the collection
            user_collection_ref = db.collection(user_id)
            delete_collection(user_collection_ref, 8)
            
def delete_collection(coll_ref, batch_size):
    docs = coll_ref.list_documents(page_size=batch_size)
    deleted = 0

    for doc in docs:
        print(f'Deleting doc {doc.id} => {doc.get().to_dict()}')
        doc.delete()
        deleted = deleted + 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        global user_id
        global items
        # get userid 
        user_id = handler_input.request_envelope.session.user.user_id
        #get current tasks
        docs = db.collection(user_id).stream()
        items = dictionaryToList(docs)
        speak_output = "Sure, I’ve opened priority planner. You can ask me to read all items on priority planner, add items, edit items, check items, or remove items. What do you want to do?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class HelloWorldIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("HelloWorldIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Hello World!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )

class ReadDefaultItemsIntentHandler(AbstractRequestHandler):
    # def __init__(self):
    #     self.speak_output = ""
    """Handler for Hello World Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("ReadDefaultItemsIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        global cur_read_idx
        global items
        
        items_num = len(items)
        cur_read_idx = -1
        if items_num == 0:
            speak_output = "There are no items on your planner yet."
        elif items_num==1:
            time = time_convert(items[0][1])
            speak_output = "There is only one item on your planner. " +items[0][0]+" by "+ time + " "+ items[0][2] +" with priority level "+str(items[0][3])+". "
            cur_read_idx = 1
        elif items_num <3:
            speak_output = "There are " +str(items_num)+ " items on your planner. "
            for i in range(items_num):
                time = time_convert(items[i][1])
                speak_output += str(i+1)+". "+items[i][0]+" by "+ time + " "+ items[i][2] +" with priority level "+str(items[i][3])+". "
            cur_read_idx = items_num
        else:
            speak_output = "There are " +str(items_num)+ " items on your planner. The first three items are: "
            for i in range(3):
                time = time_convert(items[i][1])
                speak_output += str(i+1)+". "+items[i][0]+" by "+ time + " "+ items[i][2] +" with priority level "+str(items[i][3])+". "
                # speak_output += str(i+1)+". "+items[i][0]+" by "+ items[i][1][1]+" "+items[i][1][2]+" "+ items[i][1][0] +" with priority level "+str(items[i][2])+". "
            cur_read_idx = 3
            speak_output+="If you want to hear more task, say something like read three more items, or read five more tasks."
            

        #speak_output = "read all items"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class ReadMoreItemsIntentHandler(AbstractRequestHandler):
    """Handler for  ReadMoreItemsIntent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("ReadMoreItemsIntent")(handler_input)
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        global cur_read_idx
        global items
        
        number = handler_input.request_envelope.request.intent.slots["number"].value
        total_num = len(items)
        start_idx = get_start_idx(cur_read_idx)
        end_idx = get_end_idx(cur_read_idx, int(number))
        speak_output = ""
        left_num = total_num - start_idx
        
        if start_idx == total_num:
            speak_output += "I have read all items on you list. If you want me to read those items again, say read my planner."
        elif end_idx >= total_num:
            speak_output += "You don't have that much unread items left. "
            if total_num - cur_read_idx == 1:
                speak_output += "There is only one unread item left."
            else:
                speak_output += "There are only "+str(total_num - cur_read_idx)+" unread items left."
        else:
            if int(number) == 1:
                speak_output = "The next " + number + " item on your planner is: "
            else:
                speak_output = "The next " + number + " items on your planner are: "
            for i in range(start_idx,end_idx+1):
                time = time_convert(items[i][1])
                speak_output += str(i+1)+". "+items[i][0]+" by "+ time + " "+ items[i][2] +" with priority level "+str(items[i][3])+". "
            cur_read_idx = end_idx+1
            
            
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )
def get_start_idx(cur_idx):
    return cur_idx
def get_end_idx(cur_idx,num):
    return cur_read_idx + num - 1

class ReadDayItemsIntentHandler(AbstractRequestHandler):
    """Handler for ReadDayItemsIntent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("ReadDayItemsIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        global items
        
        deadline_date = handler_input.request_envelope.request.intent.slots["deadline_date"].value
        deadline_date_str = isTodayTmrYesterday(deadline_date)
        result_items = []
        for item in items:
            if item[2] == deadline_date:
                result_items.append(item)
        result_items.sort(key = cmp_to_key(compare_by_priority))
        
        speak_output = ""
        total_num = len(result_items)
        if total_num == 0:
            speak_output += "There is no items due by "+ deadline_date_str +". "
        elif total_num == 1:
            time_str = time_convert(result_items[0][1])
            speak_output += "There is only one item due by "+ deadline_date_str +". " + result_items[0][0] + " by "+ time_str +" with priority level "+str(result_items[0][3])+". "
        else:
            speak_output = "There are " + str(total_num)+ " items due by "+ deadline_date_str +". "
            for i in range(total_num):
                time = time_convert(result_items[i][1])
                speak_output += str(i+1)+". "+result_items[i][0]+" by "+ time + " "+ result_items[i][2] +" with priority level "+str(result_items[i][3])+". "
            
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )
def compare_by_priority(i1,i2):
    time1 = i1[1].split(":")
    time2 = i2[1].split(":")
    for i in range(2):
        if time1[i] != time2[i]:
            return int(time1[i])-int(time2[i])
    # date1 = i1[2].split("-")
    # date2 = i2[2].split("-")
    # for i in range(3):
    #     if date1[i] != date2[i]:
    #         return int(date1[i])-int(date2[i])
    priority1 = int(i1[3])
    priority2 = int(i2[3])
    # if priority1 != priority2:
    return priority2-priority1


class ReadDayPIntentHandler(AbstractRequestHandler):
    """Handler for ReadDayPIntent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("ReadDayPIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        global items
        
        deadline_date = handler_input.request_envelope.request.intent.slots["deadline_date"].value
        deadline_date_str = isTodayTmrYesterday(deadline_date)
        result_items = []
        highest_p = -1
        highest_p_items = []
        for item in items:
            if item[2] == deadline_date:
                result_items.append(item)
                item_p = int(item[3])
                if item_p > highest_p:
                    highest_p_items.clear()
                    highest_p_items.append(item)
                    highest_p = item_p
                elif item_p == highest_p:
                    highest_p_items.append(item)
                    
                
        speak_output = ""
        total_num = len(result_items)
        if total_num == 0:
            speak_output += "There is no items due by "+ deadline_date_str +". "
        elif total_num == 1:
            time_str = time_convert(result_items[0][1])
            speak_output += "There is only one item due by "+ deadline_date_str +". " + result_items[0][0] + " by "+ time_str +" with priority level "+str(result_items[0][3])+". "
        else:
            speak_output = "There are " + str(total_num)+ " items due by "+ deadline_date_str +". "
            highest_p_items_num = len(highest_p_items)
            
            if highest_p_items_num == 1:
                time = time_convert(highest_p_items[0][1])
                speak_output +=   "There is only one item with the highest priority " + str(highest_p) +" due by "+ deadline_date_str+". "+ highest_p_items[0][0] + " by "+ time+". "
            else:
                speak_output += "There are " + str(highest_p_items_num)+ " items with the highest priority " + str(highest_p)+" due by "+ deadline_date_str+". "
                for i in range(highest_p_items_num):
                    time = time_convert(highest_p_items[i][1])
                    speak_output += str(i+1)+". "+highest_p_items[i][0]+" by "+ time + ". "
            
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

def isTodayTmrYesterday(date):
    # Get today's date
    presentday = datetime.now() # or presentday = datetime.today()
    # Get Yesterday
    yesterday = presentday - timedelta(1)
    # Get Tomorrow
    tomorrow = presentday + timedelta(1)
    # strftime() is to format date according to
    # the need by converting them to string
    yesterday_str = yesterday.strftime('%Y-%m-%d')
    today_str = presentday.strftime('%Y-%m-%d')
    tomorrow_str = tomorrow.strftime('%Y-%m-%d')
    if date == today_str:
        return "today"
    elif date == yesterday_str:
        return "yesterday"
    elif date == tomorrow_str:
        return "tomorrow"
    else:
        return date

class AddTaskIntentHandler(AbstractRequestHandler):
    """Handler for Add Task Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AddTaskIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "To add items, tell Alexa to save, followed by the task, deadlines and priority level."
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class SaveTaskIntentHandler(AbstractRequestHandler):
    """Handler for Save Task Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("SaveTaskIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        global items
        global user_id
        # if handler_input.request_envelope.request.intent["confirmationStatus"] == "CONFIRMED":
        task  = handler_input.request_envelope.request.intent.slots["task"].value
        deadline_time = handler_input.request_envelope.request.intent.slots["deadline_time"].value
        deadline_date = handler_input.request_envelope.request.intent.slots["deadline_date"].value
        priority = handler_input.request_envelope.request.intent.slots["priority_level"].value
        
        db.collection(user_id).document(task).set({
            u'task': task,
            u'deadline_time': deadline_time,
            u'deadline_date': deadline_date,
            u'priority': priority
        })
        # # update items
        # docs = db.collection(user_id).stream()
        # items = dictionaryToList(docs)
        
        deadline_time_str = time_convert(deadline_time)
        speak_output = "I have saved "+task+" before "+ deadline_time_str +" on "+ deadline_date +" with a priority level "+ priority+"."
        
        # add new item and sort list
        insert_items(task,deadline_time,deadline_date,priority,items)
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class EditItemIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("EditItemIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        
        speak_output = "Please say something like change the priority of task A, or change the deadline time of task A"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class EditItemTimeIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("EditItemTimeIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        global items
        global user_id
        task  = handler_input.request_envelope.request.intent.slots["task"].value
        deadline_time = handler_input.request_envelope.request.intent.slots["deadline_time"].value
        deadline_time_str = time_convert(deadline_time)
        find = editTask(task)
        if not find:
            speak_output = "I can't find this task in your planner."
        else:
            db.collection(user_id).document(task).update({
                u'deadline_time': deadline_time
            })
            idx = editNumTask(task, items)
            items[idx][1] = deadline_time
            # sort the updated list 
            items.sort(key = cmp_to_key(compare))
            speak_output = "I have changed the time for "+ task + " to "+ deadline_time_str
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class EditItemDateIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("EditItemDateIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        global items
        global user_id
        
        task  = handler_input.request_envelope.request.intent.slots["task"].value
        deadline_date = handler_input.request_envelope.request.intent.slots["deadline_date"].value
        find = editTask(task)
        if not find:
            speak_output = "I can't find this task in your planner."
        else:
            db.collection(user_id).document(task).update({
                u'deadline_date': deadline_date
            })
            idx = editNumTask(task, items)
            items[idx][2] = deadline_date
            # sort the updated list 
            items.sort(key = cmp_to_key(compare))
            speak_output = "I have changed the due date for "+ task + " to " + deadline_date
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class EditItemPIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("EditItemPIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        global items
        global user_id
        
        task  = handler_input.request_envelope.request.intent.slots["task"].value
        priority = handler_input.request_envelope.request.intent.slots["priority"].value
        find = editTask(task)
        if not find:
            speak_output = "I can't find this task in your planner."
        else:
            db.collection(user_id).document(task).update({
                u'priority': priority
            })
            idx = editNumTask(task, items)
            items[idx][3] = priority
            # sort the updated list 
            items.sort(key = cmp_to_key(compare))
            speak_output = "I have changed the priority for "+ task + " to "+ priority
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

def editTask(task):
    global user_id
    find = False
    doc_ref = db.collection(user_id).document(task)
    doc = doc_ref.get()
    if doc.exists:
        find = True
    return find

def editNumTask(task, items):
    idx = 0
    for i in range(len(items)):
        if items[i][0] == task:
            idx = i
            return idx
    return idx

class RemoveItemIntentHandler(AbstractRequestHandler):
    """Handler for Remove Item Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("RemoveItemIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        global items
        global user_id
        
        task  = handler_input.request_envelope.request.intent.slots["task"].value
        front_range = handler_input.request_envelope.request.intent.slots["front_range"].value
        position = handler_input.request_envelope.request.intent.slots["position"].value
        # docs = db.collection(u'priority_planner').stream()
        # tasks = dictionaryToList(docs)
        if task != None:
            find = removeTask(task, user_id)
            if not find:
                speak_output = "I can't find this task in your planner."
            else:
                speak_output = "I have removed "+task+" from your planner."
        elif front_range != None:
            find = removeTaskRange(front_range, items, user_id)
            if not find:
                speak_output = "You don't have that many tasks to be removed."
            else:
                speak_output = "I have removed the first "+front_range+" tasks from your planner."
        elif position != None:
            find = removeSpecificTask(position,items, user_id)
            if not find:
                speak_output = "You don't have that many tasks to be removed."
            else:
                speak_output = "I have removed the number "+ position +" task from your planner."
        else:
            speak_output = "Please say remove plus the name of the item you would like to remove."
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

def removeTask(task, user_id):
    global items
    find = False
    doc_ref = db.collection(user_id).document(task)
    doc = doc_ref.get()
    if doc.exists:
        db.collection(user_id).document(task).delete()
        find = True
    docs = db.collection(user_id).stream()
    items = dictionaryToList(docs)
    return find

def removeTaskRange(task_range, tasks, user_id):
    num = int(task_range)
    if num > len(tasks):
        return False
    else:
        while num >0:
            # tasks.pop(0)
            # num-=1
            task_name = tasks[0][0]
            db.collection(user_id).document(task_name).delete()
            tasks.pop(0)
            num-=1
        return True

def removeSpecificTask(pos, tasks, user_id):
    idx = int(pos)
    if idx>len(tasks):
        return False
    else:
        task_name = tasks[idx-1][0]
        tasks.pop(idx-1)
        db.collection(user_id).document(task_name).delete()
        return True

class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "You can say hello to me! How can I help?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )

class FallbackIntentHandler(AbstractRequestHandler):
    """Single handler for Fallback Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In FallbackIntentHandler")
        speech = "Hmm, I'm not sure. You can say Hello or Help. What would you like to do?"
        reprompt = "I didn't catch that. What can I help you with?"

        return handler_input.response_builder.speak(speech).ask(reprompt).response

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(SkillEventHandler())
sb.add_request_handler(ReadDefaultItemsIntentHandler())
sb.add_request_handler(AddTaskIntentHandler())
sb.add_request_handler(SaveTaskIntentHandler())
sb.add_request_handler(EditItemIntentHandler())
sb.add_request_handler(EditItemDateIntentHandler())
sb.add_request_handler(EditItemTimeIntentHandler())
sb.add_request_handler(EditItemPIntentHandler())
sb.add_request_handler(RemoveItemIntentHandler())
sb.add_request_handler(ReadDayItemsIntentHandler())
sb.add_request_handler(ReadDayPIntentHandler())
sb.add_request_handler(ReadMoreItemsIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()