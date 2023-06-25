#!/usr/bin/env python3
import sys
import os
import time
import argparse
import requests
from datetime import datetime
from urllib.parse import urlparse
from termcolor import colored


def append_http(url, port=None):
    if "https://" in url:
        url = f"{url}"
    elif "http://" not in url:
        o = urlparse(f"http://{url}")
        if o.port:
            url = f"http://{url}"
        else:
            url = f"http://{url}:{port}"
    return url


def get_loopchain_state(ipaddr="localhost", port=os.environ.get('RPC_PORT', 9000)):
    url = append_http(ipaddr, port) + "/admin/chain"
    return_result = {}
    try:
        session = requests.Session()
        r = session.get(url, verify=False, timeout=10)
        return_result = r.json()[0]
        return_result['prev_time'] = time.time()
        return_result['url'] = url
    except Exception as e:
        print(f"Error while connecting server... {url}: {str(e)}")
        return_result = {
            "block_height": 0
        }
    return return_result


def disable_ssl_warnings():
    from urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def print_status(count, block_diff, sync_speed, finish_block_height, finish_time):
    status = f"({count})   BlockDiff [{block_diff}]    SyncSpeed [{sync_speed:.0f}]    FinishHeight [{finish_block_height:.0f}]    FinishTime [{finish_time}]"
    if sync_speed == 0:
        return colored(status, 'red')
    return colored(status, 'green')


if __name__ == '__main__':
    disable_ssl_warnings()
    parser = argparse.ArgumentParser(prog='checker')
    parser.add_argument('url', nargs='?', default="localhost:9000")
    parser.add_argument('-n', '--network', type=str, help='parent network type (mainnet|berlin|sejong|lisbon)', default="mainnet")
    parser.add_argument('-v', '--verbose', action='count', help='verbose mode. view level', default=0)
    parser.add_argument('-c', '--count', type=int, help='check count(sec).', default=0)

    args = parser.parse_args()

    network_info = {
        "mainnet": "http://52.196.159.184:9000",
        "berlin": "https://berlin.net.solidwallet.io",
        "sejong": "https://sejong.net.solidwallet.io",
        "lisbon": "https://lisbon.net.solidwallet.io",
        "havah": "https://ctz.havah.io",
        "vega": "https://ctz.vega.havah.io",
    }

    if os.environ.get('SERVICE', None):
        args.network = os.environ['SERVICE']
    elif os.environ.get('NETWORK_ENV', None):
        args.network = os.environ['NETWORK_ENV']

    if args.network in network_info.keys():
        parent_network_url = network_info.get(args.network)
    else:
        parent_network_url = args.network

    block_diff = 0
    block_diff2 = 0
    network_block_height = 0
    first_block_height = 0
    second_block_height = 0
    finish_block_height = 0
    prev_time = 0
    sync_speed = 0
    height = 0
    count = 0

    print(f"Target peer: {args.url}")
    if args.verbose > 0:
        print(f"Get parent status from {parent_network_url}")

    first_block_height, first_prevtime = get_loopchain_state(args.url)["height"], get_loopchain_state(args.url)["prev_time"]

    try:
        while True:
            count += 1
            second_block_height, second_prevtime = get_loopchain_state(args.url)["height"], get_loopchain_state(args.url)["prev_time"]
            network_block_height, prevtime = get_loopchain_state(parent_network_url)["height"], get_loopchain_state(parent_network_url)["prev_time"]

            block_diff = network_block_height - second_block_height
            block_diff2 = second_block_height - first_block_height
            sync_speed = block_diff2 / (second_prevtime - first_prevtime) if first_prevtime != 0 and second_prevtime != first_prevtime else 0
            finish_block_height = (block_diff / sync_speed / 2 + network_block_height) if sync_speed != 0 else float('inf')
            finish_time = datetime.fromtimestamp(int(((finish_block_height - second_block_height) / sync_speed) + time.time())) if sync_speed != 0 and finish_block_height != float('inf') else 'N/A'

            status = print_status(count, block_diff, sync_speed, finish_block_height, finish_time)
            sys.stdout.write('\r' + status)
            sys.stdout.flush()

            if count == args.count:
                break

            time.sleep(1)
    except KeyboardInterrupt:
        print("\nProgram interrupted. Exiting...")
        sys.exit(0)
