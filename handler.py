import json
import json
import requests
import boto3  # AWS SDK for Python
from botocore.exceptions import ClientError
import datetime
from jproperties import Properties
configs = Properties()

def hello(event, context):
    with open('app-config.properties', 'rb') as config_file:
        configs.load(config_file)

    client = boto3.client('lexv2-runtime',region_name='us-east-1')
    
    try:
        body = json.loads(event["body"])  # Parse JSON body from event
        print("# body:", body)  # Log for debugging
        
        message_for_lex = map_telegram_to_lex(body)
        print("## message_for_lex: ", message_for_lex)
        print("## message_for_lex['botId']: ", message_for_lex['botId'])
        print("## message_for_lex['botAliasId']: ", message_for_lex['botAliasId'])

        now = datetime.datetime.now()
        # Creating unique session id for differents chats: combining YYYY_MM_DD_HH24
        unique_session_id = str(body["message"]["chat"]["id"]) + '_' + str(now.year) + '_' + str(now.month) + '_' + str(now.day) + '_' + str(now.hour)
                                
        print(now.year, now.month, now.day, now.hour, now.minute, now.second)
        
        lex_response = client.recognize_text(
            botId = message_for_lex['botId'],
            botAliasId = message_for_lex['botAliasId'],
            localeId = message_for_lex['localeId'],
            sessionId = unique_session_id,
            text = message_for_lex['text'])
        
        print("#########")
        if 'sessionState' in lex_response:
            sessionState = lex_response['sessionState']
            print('### sessionState: ')
            print( sessionState)
            if 'intent' in sessionState:
                intent = sessionState['intent'] 
                print("#### Intent: ")
                print(intent)
                if 'name' in intent:
                    name = intent['name']
                    print('#### name: ')
                    print(name)
                else:        
                    print("### The 'name' property does not exist.")
            else:
                print("### The 'intent' property does not exist.")
            
            if 'dialogAction' in sessionState:
                dialogAction = sessionState['dialogAction']
                print('#### dialogAction: ')
                print(dialogAction)

                if 'type' in dialogAction:
                    type = dialogAction['type']
                    print('##### type: ')
                    print(type)

                    if type == 'ConfirmIntent':
                        lex_session_response = client.get_session(
                            botId=configs.get("BOT_ID"),
                            botAliasId=configs.get("BOT_ALIAS_ID"),
                            localeId=configs.get("en_US"),
                            sessionId=unique_session_id
                        )
                        interpretations = lex_session_response['interpretations']
                        intent = interpretations[0]['intent']
                        print('##### intent: ', intent)
                        print('##### name: ', intent['name'])
                        print('##### slots: ', intent['slots'])
                        
                        slots = intent['slots']
                        issueDate= slots['IssueDate']['value']['interpretedValue']
                        issueDescription = slots['IssueDescription']['value']['interpretedValue']
                        issueSeverity = slots['IssueSeverity']['value']['interpretedValue']
                        
                        print('##### issueDate: ', issueDate)
                        print('##### issueDescription: ', issueDescription)
                        print('##### IssueSeverity: ', issueSeverity)

                        pivotal_tracker_url = 'https://www.pivotaltracker.com/services/v5/projects/'+configs.get("PIVOTAL_TRACKER_PROJECTID")+'/stories/'

                        pivotal_tracker_headers = {"X-TrackerToken": "261d696699f92e1c26a3166a43611991", "Content-Type": "application/json"}

                        pivotal_tracker_data = {
                            "current_state": "started",
                            "estimate": 1,
                            "name": issueDescription
                        }
                        
                        print('###### pivotal_tracker_headers: ', pivotal_tracker_headers)
                        print('###### pivotal_tracker_url: ', pivotal_tracker_url)
                        print('###### pivotal_tracker_data: ', pivotal_tracker_data)

                        pivotal_tracker_response = requests.post(pivotal_tracker_url, headers=pivotal_tracker_headers, json=pivotal_tracker_data)

                        print('####### pivotal_tracker_response: ', json.dumps(pivotal_tracker_response))

                    else:
                        print('###### No ConfirmIntent: ')

                else:
                    print("##### The 'type' property does not exist.")

                if 'slotToElicit' in dialogAction:
                    slotToElicit = dialogAction['slotToElicit']
                    print('##### slotToElicit: ')
                    print(slotToElicit)
                else:
                    print("##### The 'slotToElicit' property does not exist.")
            else:
                print("### The 'dialogAction' property does not exist.")

        else:
            print("### The 'sessionState' property does not exist.")
        print("#########")

        print("#########")
        if 'messages' in lex_response:
            messages = lex_response['messages']
            print('### messages: ')
            print(messages)
            print("### Prompt or Msg:",messages[0]['content'])
        else:
            print("### The 'messages' property does not exist.")
        print("#########")

        # print("### lex_response: ", lex_response)
        # print("#### Intent:",lex_response['sessionState']['intent']['name'])
        # print("#### Next Action:",lex_response['sessionState']['dialogAction']['type'])
        # print("#### Next Slot:",lex_response['sessionState']['dialogAction']['slotToElicit'])
        # print("#### Prompt or Msg:",lex_response['messages'][0]['content'])
        print("#### Chat ID: ", body["message"]["chat"]["id"])
        
        
        message_for_telegram = map_lex_to_telegram(lex_response, body)
        print("#########")
        print("message_for_telegram: ", message_for_telegram)
        print("#########")

        send_to_telegram(message_for_telegram)
        
    except ClientError as e:
        print("AWS Lex error:", e)
    except json.JSONDecodeError as e:
        print("JSON parsing error:", e)
    except Exception as e:  # Catch any other unexpected errors
        print("Unexpected error:", e)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
        

def map_telegram_to_lex(body):
    with open('app-config.properties', 'rb') as config_file:
        configs.load(config_file)
    
    chat_id = str(body["message"]["chat"]["id"])
    message = body["message"]["text"]

    return {
        "botName": configs.get("BOT_NAME"),
        "botId": configs.get("BOT_ID"),
        "botAliasId": configs.get("BOT_ALIAS_ID"), 
        "localeId": configs.get("LOCALE_ID"),
        "userId": chat_id,
        "sessionAttributes": {},
        "text": message
    }

def map_lex_to_telegram(lex_response, body):
    return {
        "text": lex_response['messages'][0]['content'],
        "chat_id": body["message"]["chat"]["id"],
    }


def send_to_telegram(message):
    with open('app-config.properties', 'rb') as config_file:
        configs.load(config_file)

    telegramToken = configs.get("TELEGRAM_TOKEN")
    telegramApiUrl = configs.get("TELEGRAM_API_URL")
    url = telegramApiUrl.format(telegramToken)
    return requests.post(url, data=message)

