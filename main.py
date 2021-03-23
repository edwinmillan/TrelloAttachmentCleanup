import requests
import re
import json
import configparser
from trello import TrelloApi, Cards
from typing import List, Optional, Iterable, NoReturn


class TrelloCards(Cards):
    def __init__(self, apikey, token=None):
        super(TrelloCards, self).__init__(apikey, token)

    def update_attachment(self, card_id_or_shortlink: str, attachment_id: str, data: dict):
        resp = requests.put(f"https://trello.com/1/cards/{card_id_or_shortlink}/attachments/{attachment_id}",
                            params={"key": self._apikey, "token": self._token}, data=data)
        return self.raise_or_json(resp)


class Trello(TrelloApi):
    def __init__(self, apikey, token=None):
        super(Trello, self).__init__(apikey, token)
        self.cards = TrelloCards(apikey, token)


def get_target_board(trello: Trello, board_name: str) -> Optional[dict]:
    my_boards = trello.members.get_board('me')
    api_filter = tuple(filter(lambda b: b.get('name') == board_name, my_boards))
    if api_filter:
        return api_filter[0]
    else:
        return tuple()


def filter_target_list(board_lists: List[dict], board_name: str) -> Optional[dict]:
    for board_list in board_lists:
        if board_list.get('name') == board_name:
            return board_list


def get_list_info(trello: Trello, api_board_info: dict, target_list_name: str) -> Optional[dict]:
    board_id = api_board_info.get('id')
    board_lists = trello.boards.get_list(board_id)
    return filter_target_list(board_lists, target_list_name)


def remove_file_extension(file_name: str) -> str:
    match = re.search(r'(.+)\.\S+', file_name)
    if match:
        return match[1]
    else:
        return file_name


def update_board_attachments(trello: Trello, board_name: str, target_list_names: Iterable) -> NoReturn:
    board_info = get_target_board(trello, board_name=board_name)
    if board_info:
        print(f"Working on Board: {board_name}")
        # Go through each list names and update each card's attachments
        for list_name in target_list_names:
            # Get the dict holding the list ID using the board.
            list_info = get_list_info(trello=trello, api_board_info=board_info, target_list_name=list_name)
            if list_info:
                print(f"Working on List: {list_info.get('name')}")
                list_id = list_info.get('id')
                # Get the list of cards
                list_cards = trello.lists.get_card(list_id)
                # Iterates over each card and gets the attachments.
                for card in list_cards:
                    print(f"\tLooking through card: {card.get('name')}")
                    card_id = card.get('id')
                    attachments = trello.cards.get_attachment(card_id)
                    for attachment in attachments:
                        attachment_id = attachment.get('id')
                        raw_name = attachment.get('name')
                        # If the name has an ext, return a version without the ext.
                        parsed_name = remove_file_extension(raw_name)
                        # If it's not already fixed, go update it via the API.
                        if raw_name and parsed_name != raw_name:
                            print(f"\t\tUpdating attachment: {raw_name} -> {parsed_name}")
                            payload = {'name': parsed_name}
                            trello.cards.update_attachment(card_id_or_shortlink=card_id,
                                                           attachment_id=attachment_id, data=payload)
    else:
        print('No Board info found')


def load_credentials(credential_json: str) -> (str, str):
    with open(credential_json, 'r') as cred_file:
        creds = json.load(cred_file)
        return creds.get('key'), creds.get('token')


def load_config_settings(config_filename: str) -> (str, Iterable):
    config = configparser.ConfigParser()
    config.read(config_filename)
    settings = config['settings']

    target_board_name = settings['board_name']
    target_list_names = map(str.strip, settings['list_names'].split(','))
    return target_board_name, target_list_names


def main() -> NoReturn:
    key, token = load_credentials('token.json')
    target_board_name, target_list_names = load_config_settings(config_filename='config.ini')

    trello = Trello(apikey=key, token=token)
    update_board_attachments(trello, target_board_name, target_list_names)


if __name__ == '__main__':
    main()
