
import typing as t
from abc import ABC

import requests as r
import socket
import csv
import json
import os
import time
import csv
import re
import _thread as thread

from websocket import create_connection
import websocket


class DraftClient(ABC):

    def __init__(self, draft_id: str):
        self._draft_id = draft_id
        url = 'ws://localhost:7000/ws/draft/{}/'.format(
            self._draft_id
        )

        self._ws = websocket.WebSocketApp(
            url,
            on_message = self.on_message,
            on_error = self.on_error,
            on_close = self.on_close,
        )
        self._ws.on_open = self.on_open
        self._ws.run_forever()


    def on_error(self, error):
        print(error)

    def on_close(self):
        print("### closed ###")

    def on_open(self):
        pass
        # self._ws.send(
        #     json.dumps(
        #         {
        #             'type': 'authentication',
        #             'token': 'cb14f2cb8f73ea356d0cb82e04f4f4219a3bb580b7582b4e23427637257a973f',
        #         }
        #     )
        # )

    def on_message(self, message):
        message = json.loads(message)
        print(message)
        message_type = message['type']

        if message_type == 'booster':
            cubeables = list(message['booster'])
            print('----------')
            for index, cubeable in enumerate(cubeables):
                print(index, cubeable)
            print('----------')
            while True:
                idx = input(': ')
                try:
                    idx = int(idx)
                except ValueError:
                    continue
                if idx >= len(cubeables):
                    continue
                self._ws.send(
                    json.dumps(
                        {
                            'type': 'pick',
                            'pick': cubeables[idx],
                        }
                    )
                )
                break