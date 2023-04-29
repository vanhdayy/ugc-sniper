# made by xolo#4942
# version 10.2.9

try:
 try:
  import logging
  import traceback
  import datetime
  import os
  import uuid
  import asyncio
  import random
  import requests
  from colorama import Fore, Back, Style
  import aiohttp
  import json
  import discord
  from discord.ext import commands
  import themes
  import time
 except ModuleNotFoundError:
    print("Modules not installed properly installing now")
    os.system("pip install requests")
    os.system("pip install colorama")
    os.system("pip install colorama")
    os.system("pip install aiohttp")
    os.system("pip install rapidjson")
    os.system("pip install discord")
    os.system("pip install logging")
 
 
 logging.basicConfig(filename='logs.txt', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
 logger = logging.getLogger(__name__)
 logger.setLevel(logging.DEBUG)

 formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

 handler = logging.StreamHandler()
 handler.setLevel(logging.DEBUG)
 handler.setFormatter(formatter)

 logger.addHandler(handler)


 if os.name == 'nt':
     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
       
 class Sniper:
    class bucket:
        def __init__(self, max_tokens: int, refill_interval: float):
            self.max_tokens = max_tokens
            self.tokens = max_tokens
            self.refill_interval = refill_interval
            self.last_refill_time = asyncio.get_event_loop().time()

        async def take(self, tokens: int, proxy=False):
            while True:
                if proxy:
                    return True
                
                elapsed = asyncio.get_event_loop().time() - self.last_refill_time
                if elapsed > self.refill_interval:
                   self.tokens = self.max_tokens
                   self.last_refill_time = asyncio.get_event_loop().time()

                if self.tokens >= tokens:
                   self.tokens -= tokens
                   return
                else:
                   await asyncio.sleep(0.01)
                   
    class ProxyHandler:
       class TokenBucket:
            def __init__(self, capacity, rate):
                self.capacity = capacity
                self.tokens = capacity
                self.rate = rate
                self.timestamp = time.monotonic()

            def consume(self):
                now = time.monotonic()
                elapsed_time = now - self.timestamp
                self.timestamp = now
                new_tokens = elapsed_time * self.rate
                if new_tokens > 0:
                   self.tokens = min(self.tokens + new_tokens, self.capacity)
                if self.tokens >= 1:
                   self.tokens -= 1
                   return True
                return False
            
       def __init__(self, proxies, requests_per_minute):
        self.proxies = proxies
        self.token_buckets = {proxy: self.TokenBucket(requests_per_minute, requests_per_minute/60) for proxy in proxies}
        self.current_proxy_index = 0

       def get_next_proxy(self):
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        proxy = self.proxies[self.current_proxy_index]
        return proxy

       async def newprox(self):
        while True:
            proxy = self.proxies[self.current_proxy_index]
            if self.token_buckets[proxy].consume():
                return proxy
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)  
        
                      
    def __init__(self) -> None:
        logging.info("Started Sniper Class")
        with open("config.json") as file:
             self.config = json.load(file)
        
        self.ratelimit = self.bucket(max_tokens=60, refill_interval=60)    
        self.webhookEnabled = False if not self.config["webhook"] or self.config["webhook"]["enabled"] == False else True
        self.webhookUrl = self.config["webhook"]["url"] if self.webhookEnabled else None
        self.accounts = None
        self.items = self._load_items()
        self.checks = 0
        self.buys = 0
        self.request_method = 2
        self.last_time = 0
        self.errors = 0
        self.clear = "cls" if os.name == 'nt' else "clear"
        self.version = "10.2.9"
        self.task = None
        self.timeout = self.config['proxy']['timeout_ms'] / 1000 if self.config['proxy']["enabled"] else None
        self.latest_free_item = {}
        self._setup_accounts()
        self.check_version()
        self.tasks = {}
        self.themeWaitTime = float(self.config.get('theme')['wait_time'])
        self.proxies = []
        self.proxy_auth = None
        if self.config['proxy']['enabled']:
            logging.info("Proxy enabled")
            self.proxy_auth = aiohttp.BasicAuth(self.config['proxy']['authentication']['username'], self.config['proxy']['authentication']['password']) if self.config['proxy']['authentication']['enabled'] else None
            with open(self.config['proxy']['proxy_list']) as f:
                lines = [line.strip() for line in f if line.rstrip()]
            response = asyncio.run(self.check_all_proxies(lines))
            self.proxies = response
            self.proxy_handler = self.ProxyHandler(self.proxies, 60)

        if self.config.get("discord", False)['enabled']:
            self.run_bot()
        else:
            asyncio.run(self.start())
    
    async def check_proxy(self, proxy):
        try:
          async with aiohttp.ClientSession() as session:
            response = await session.get('https://google.com/', timeout=self.timeout, proxy=f"http://{proxy}", proxy_auth = self.proxy_auth)
            if response.status_code == 200:
                return proxy
        except:
            pass

    async def check_all_proxies(self, proxies):
        logging.info("Checking all proxies")
        tasks = []
        for proxy in proxies:
            task = asyncio.create_task(self.check_proxy(proxy))
            tasks.append(task)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        working_proxies = []
        for result in results:
            if result is not None:
               working_proxies.append(result)
        return working_proxies
    
    def run_bot(self):
        bot = commands.Bot(command_prefix=self.config.get('discord')['prefix'], intents=discord.Intents.all())
        
        @bot.command(name="queue")
        async def queue(ctx):
            return await ctx.reply(self.items)
        
        @bot.command(name="stats")
        async def stats(ctx):
            embed = discord.Embed(title="xolo sniper", color=0x00ff00)
            embed.set_author(name=f"Version: {self.version}")
            embed.add_field(name="Loaded items", value=f"{len(self.items)}", inline=True)
            embed.add_field(name="Total buys", value=f"{self.buys}", inline=True)
            embed.add_field(name="Total errors", value=f"{self.errors}", inline=True)
            embed.add_field(name="Last speed", value=f"{self.last_time}", inline=True)
            embed.add_field(name="Total price checks", value=f"{self.checks}", inline=True)
            embed.add_field(name="Current task", value=f"{self.task}", inline=False)
            return await ctx.reply(embed=embed)
        
        @bot.command(name="remove_id")
        async def remove_id(ctx, arg=None):
                    
            if arg is None:
                return await ctx.reply("You need to enter a id to remove")
            
            if not arg.isdigit():
                        return await ctx.reply(f"Invalid item id given ID: {arg}")
                        
            if not arg in self.tasks:
                print(self.tasks)
                return await ctx.reply("Id is not curently running")
            
            self.tasks[arg].cancel()
            del self.items[arg]
            del self.tasks[arg]
            for item in self.config["items"]:
                if item["id"] == arg:
                    self.config["items"].remove(item)
                    break
                
            with open('config.json', 'w') as f:
                json.dump(self.config, f, indent=4)
            logging.debug(f"removed item id {arg}")
            return await ctx.reply("Id successfully removed")
            
        @bot.command(name="add_id")
        async def add_id(ctx, id=None, start=None, end=None, max_price=None, max_buys=None, importance = None):
            if id is None:
               return await ctx.reply("You need to enter an ID to add")

            if not id.isdigit():
                        return await ctx.reply(f"Invalid item id given ID: {id}")
                        
            if id in self.tasks:
               return await ctx.reply("ID is currently running")
            
            self.config['items'].append({
                "id": id,
                "start": None if start is None else start,
                "end": None if end is None else end,
                "max_price": None if max_price is None else int(max_price),
                "max_buys": None if max_buys is None else int(max_buys),
                "importance": 1 if importance is None or not int(importance) > 0 else int(importance)
            })
            with open('config.json', 'w') as f:
                 json.dump(self.config, f, indent=4)
            self.items[id] = {}
            self.items[id]['current_buys'] = 0
            for item in self.config["items"]:
                if int(item['id']) == int(id):
                    item = item
                    break
            self.items[id]['max_buys'] = float('inf') if item['max_buys'] is None else int(item['max_buys'])
            self.items[id]['max_price'] = float('inf') if item['max_price'] is None else int(item['max_price'])
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=None)) as session:
                
                await ctx.reply("ID successfully added")
                logging.debug(f"added item id {id}")
                self.tasks[id] = asyncio.create_task(self.search(session=session, id=id))
                await asyncio.gather(self.tasks[id])

            
            
        @bot.event
        async def on_ready():
            await self.start()
            
        bot.run(self.config.get('discord')['token'])
              
    def check_version(self):
        logging.debug(f"Checking Version")
        self.task = "Github Checker"
        self._print_stats()
        response = requests.get("https://raw.githubusercontent.com/efenatuyo/ugc-sniper/main/version")
        if response.status_code != 200:
            pass
        print(response.text.rstrip())
        if not response.text.rstrip() == self.version:
                print("NEW UPDATED VERSION PLEASE UPDATE YOUR FILE")
                print("will continue in 5 seconds")
                import time
                time.sleep(5)
        
    class DotDict(dict):
        def __getattr__(self, attr):
            return self[attr]
    
    def wait_time(self, item_id=None, proxy=False):
        items = self.config['items']
        if item_id:
           item = next((item for item in items if item['id'] == item_id), None)
           if not item:
              return None
           importance = item.get('importance', 1)
           total_importance = importance
           num_items = 1
        else:
           importance = 1
           total_importance = sum(item.get('importance', 1) for item in items)
           num_items = len(items)
    
        wait_time = (num_items * importance / total_importance)
        
        if proxy:
            return wait_time * 0.25
        return wait_time
    
    def _setup_accounts(self) -> None:
        logging.info(f"Setting up accounts")
        self.task = "Account Loader"
        self._print_stats
        cookies = self._load_cookies()
        for i in cookies:
              response = asyncio.run(self._get_user_id(cookies[i]["cookie"]))
              response2 = asyncio.run(self._get_xcsrf_token(cookies[i]["cookie"]))
              cookies[i]["id"] = response
              cookies[i]["xcsrf_token"] = response2["xcsrf_token"]
              cookies[i]["created"] = response2["created"]
        self.accounts = cookies
        
    def _load_cookies(self) -> dict:
            lines = self.config['accounts']
            my_dict = {}
            for i, line in enumerate(lines):
                my_dict[str(i+1)] = {}
                my_dict[str(i+1)] = {"cookie": line['cookie']}
            return my_dict
        
    def _load_items(self) -> list:
            dict = {}
            for item in self.config["items"]:
                dict[item['id']] = {}
                dict[item['id']]['current_buys'] = 0
                dict[item['id']]['max_buys'] = float('inf') if item['max_buys'] is None else int(item['max_buys'])
                dict[item['id']]['max_price'] = float('inf') if item['max_price'] is None else int(item['max_price'])
            return dict
                 
    async def _get_user_id(self, cookie) -> str:
       async with aiohttp.ClientSession(cookies={".ROBLOSECURITY": cookie}) as client:
           response = await client.get("https://users.roblox.com/v1/users/authenticated", ssl = False)
           data = await response.json()
           if data.get('id') == None:
              raise Exception("Couldn't scrape user id. Error:", data)
           return data.get('id')
    
    def _print_stats(self) -> None:
        function_name = self.config['theme']['name']
        module = getattr(themes, function_name)
        function = getattr(module, '_print_stats')
        function(self)
            
    async def _get_xcsrf_token(self, cookie) -> dict:
        logging.debug(f"Scraped x_token")
        async with aiohttp.ClientSession(cookies={".ROBLOSECURITY": cookie}) as client:
              response = await client.post("https://accountsettings.roblox.com/v1/email", ssl = False)
              xcsrf_token = response.headers.get("x-csrf-token")
              if xcsrf_token is None:
                 raise Exception("An error occurred while getting the X-CSRF-TOKEN. "
                            "Could be due to an invalid Roblox Cookie")
              return {"xcsrf_token": xcsrf_token, "created": datetime.datetime.now()}
    
    async def _check_xcsrf_token(self) -> bool:
      for i in self.accounts:
        if self.accounts[i]["xcsrf_token"] is None or \
                datetime.datetime.now() > (self.accounts[i]["created"] + datetime.timedelta(minutes=10)):
            try:
                response = await self._get_xcsrf_token(self.accounts[i]["cookie"])
                self.accounts[i]["xcsrf_token"] = response["xcsrf_token"]
                self.accounts[i]["created"] = response["created"]
                return True
            except Exception as e:
                print(f"{e.__class__.__name__}: {e}")
                return False
        return True
      return False
     
    async def buy_item(self, item_id: int, price: int, user_id: int, creator_id: int,
         product_id: int, cookie: str, x_token: str, raw_id: int) -> None:
        
         """
            Purchase a limited item on Roblox.
            Args:
                item_id (int): The ID of the limited item to purchase.
                price (int): The price at which to purchase the limited item.
                user_id (int): The ID of the user who will be purchasing the limited item.
                creator_id (int): The ID of the user who is selling the limited item.
                product_id (int): The ID of the product to which the limited item belongs.
                cookie (str): The .ROBLOSECURITY cookie associated with the user's account.
                x_token (str): The X-CSRF-TOKEN associated with the user's account.
         """
        
        
         data = {
               "collectibleItemId": item_id,
               "expectedCurrency": 1,
               "expectedPrice": price,
               "expectedPurchaserId": user_id,
               "expectedPurchaserType": "User",
               "expectedSellerId": creator_id,
               "expectedSellerType": "User",
               "idempotencyKey": "random uuid4 string that will be your key or smthn",
               "collectibleProductId": product_id
         }
         total_errors = 0
         await asyncio.to_thread(logging.info, "New Buy Thread Started")
         async with aiohttp.ClientSession() as client:   
            while True:
                if not float(self.items[raw_id]['max_buys']) > float(self.items[raw_id]['current_buys']):
                    del self.items[id]
                    for item in self.config['items']:
                        if str(item['id']) == (raw_id):
                           self.config["items"].remove(item)
                           break
                
                    with open('config.json', 'w') as f:
                        json.dump(self.config, f, indent=4)
                    return
                if total_errors >= 10:
                    print("Too many errors encountered. Aborting purchase.")
                    return
                 
                data["idempotencyKey"] = str(uuid.uuid4())
                
                try:
                    response = await client.post(f"https://apis.roblox.com/marketplace-sales/v1/item/{item_id}/purchase-item",
                           json=data,
                           headers={"x-csrf-token": x_token},
                           cookies={".ROBLOSECURITY": cookie}, ssl = False)
                
                except aiohttp.ClientConnectorError as e:
                    self.errors += 1
                    print(f"Connection error encountered: {e}. Retrying purchase...")
                    total_errors += 1
                    continue
                    
                if response.status == 429:
                       print("Ratelimit encountered. Retrying purchase in 0.5 seconds...")
                       await asyncio.sleep(0.5)
                       continue
            
                try:
                      json_response = await response.json()
                except aiohttp.ContentTypeError as e:
                      self.errors += 1
                      print(f"JSON decode error encountered: {e}. Retrying purchase...")
                      total_errors += 1
                      continue
                  
                if not json_response["purchased"]:
                       self.errors += 1
                       print(f"Purchase failed. Response: {json_response}. Retrying purchase...")
                       total_errors += 1
                       if json_response.get("errorMessage", 0) == "QuantityExhausted":
                           return
                else:
                       self.items[raw_id]['current_buys'] += 1
                       for item in self.config['items']:
                           if int(item['id']) == raw_id:
                               self.config["items"].remove(item)
                               
                       print(f"Purchase successful. Response: {json_response}.")
                       self.buys += 1
                       if self.webhookEnabled:
                            embed_data = {
                                "title": "New Item Purchased with Xolo Sniper",
                                "url": f"https://www.roblox.com/catalog/{item_id}/Xolo-Sniper",
                                "color": 65280,
                                "author": {
                                    "name": "Purchased limited successfully!"
                                },
                                "footer": {
                                "text": "Xolo's Sniper"
                                }
                            }

                            requests.post(self.webhookUrl, json={"content": None, "embeds": [embed_data]})

    async def auto_search(self) -> None:
     async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=None)) as session:
      while True:
        try:
            await self.ratelimit.take(1, proxy = True if self.proxies is not None and len(self.proxies) > 0 else False)
            async with session.get("https://catalog.roblox.com/v2/search/items/details?Keyword=orange%20teal%20cyan%20red%20green%20topaz%20yellow%20wings%20maroon%20space%20dominus%20lime%20mask%20mossy%20wooden%20crimson%20salmon%20brown%20pastel%20%20ruby%20diamond%20creatorname%20follow%20catalog%20link%20rare%20emerald%20chain%20blue%20deep%20expensive%20furry%20hood%20currency%20coin%20royal%20navy%20ocean%20air%20white%20cyber%20ugc%20verified%20black%20purple%20yellow%20violet%20description%20dark%20bright%20rainbow%20pink%20cyber%20roblox%20multicolor%20light%20gradient%20grey%20gold%20cool%20indigo%20test%20hat%20limited2%20headphones%20emo%20edgy%20back%20front%20lava%20horns%20water%20waist%20face%20neck%20shoulders%20collectable&Category=11&Subcategory=19&CurrencyType=3&MaxPrice=0&salesTypeFilter=2&SortType=3&limit=120", ssl = False) as response:
                  response.raise_for_status()
                   
                  items = (json.loads(await response.text())['data'])
                  
                  for item in items:
                      if item["id"] not in self.scraped_ids:
                          print(f"Found new free item: {item['name']} (ID: {item['id']})")
                          self.latest_free_item = item
                          self.scraped_ids.append(item)
                          
                          if self.latest_free_item.get("priceStatus", "Off Sale") == "Off Sale":
                            continue
                        
                          if self.latest_free_item.get("collectibleItemId") is None:
                              continue
                          await self.ratelimit.take(1, proxy = True if self.proxies is not None and len(self.proxies) > 0 else False)
                          productid_response = await session.post("https://apis.roblox.com/marketplace-items/v1/items/details",
                                     json={"itemIds": [self.latest_free_item["collectibleItemId"]]},
                                     headers={"x-csrf-token": self.accounts[str(random.randint(1, len(self.accounts)))]["xcsrf_token"], 'Accept': "application/json"},
                                     cookies={".ROBLOSECURITY": self.accounts[str(random.randint(1, len(self.accounts)))]["cookie"]}, ssl = False)
                          response.raise_for_status()
                          productid_data = json.loads(await  productid_response.text())[0]
                          coroutines = [self.buy_item(item_id = self.latest_free_item["collectibleItemId"], price = 0, user_id = self.accounts[i]["id"], creator_id = self.latest_free_item['creatorTargetId'], product_id = productid_data['collectibleProductId'], cookie = self.accounts[i]["cookie"], x_token = self.accounts[i]["xcsrf_token"]) for i in self.accounts] * 4
                          self.task = "Item Buyer"
                          await asyncio.gather(*coroutines)
                          
        except aiohttp.client_exceptions.ClientConnectorError as e:
            print(f"Error connecting to host: {e}")
            self.errors += 1
        except aiohttp.client_exceptions.ServerDisconnectedError as e:
            print(f"Server disconnected error: {e}")
            self.errors += 1
        except aiohttp.client_exceptions.ClientOSError as e:
            print(f"Client OS error: {e}")
            self.errors += 1
        except aiohttp.client_exceptions.ClientResponseError as e:
            print(f"Response Error: {e}")
            self.errors += 1
            await asyncio.sleep(5)
        finally:
            self.checks += 1
            await asyncio.sleep(5)
            
    async def search(self, session, id, ) -> None:
      for item in self.config["items"]:
          itemo = item
          if item["id"] == id:
              start_date  = item['start']
              end_date = item['end']
      while True:
        try:
                    if self.config['proxy']['enabled'] and len(self.proxies) > 0:
                        proxy = f"http://{await self.proxy_handler.newprox()}"
                    else:
                        proxy = None
                    try:
                      start_time = datetime.datetime.strptime(str(start_date), "%Y-%m-%d %H:%M:%S")
                      print(start_time)
                      if datetime.datetime.now() >= start_time:
                         end_date = datetime.datetime.strptime(str(end_date), "%Y-%m-%d %H:%M:%S")
                         if end_date >= datetime.datetime.now():
                           pass
                         else:
                             del self.items[id]
                             self.config["items"].remove(itemo)
                
                             with open('config.json', 'w') as f:
                                json.dump(self.config, f, indent=4)
                             return
                      else:
                         continue
                    except Exception as e:
                         pass
                    self.task = "Item Scraper & Searcher"
                    t0 = asyncio.get_event_loop().time()
                
                    if not id.isdigit():
                        raise Exception(f"Invalid item id given ID: {id}")
                    await self.ratelimit.take(1, proxy = True if self.proxies is not None and len(self.proxies) > 0 else False)
                    currentAccount = self.accounts[str(random.randint(1, len(self.accounts)))]
                    async with session.post("https://catalog.roblox.com/v1/catalog/items/details",
                                           json={"items": [{"itemType": "Asset", "id": id}]},
                                           headers={"x-csrf-token": currentAccount['xcsrf_token'], 'Accept': "application/json"},
                                           cookies={".ROBLOSECURITY": currentAccount["cookie"]}, ssl=False, proxy=proxy, timeout=self.timeout, proxy_auth = self.proxy_auth) as response:
                        response.raise_for_status()
                        response_text = await response.text()
                        json_response = json.loads(response_text)['data'][0]
                        if int(json_response.get("price", 0)) > self.items[id]['max_price']:
                             del self.items[id]
                             self.config["items"].remove(itemo)
                
                             with open('config.json', 'w') as f:
                                json.dump(self.config, f, indent=4)
                             return
                        if json_response.get("priceStatus") != "Off Sale" and json_response.get('unitsAvailableForConsumption', 0) > 0:
                            await self.ratelimit.take(1, proxy = True if self.proxies is not None and len(self.proxies) > 0 else False)
                            productid_response = await session.post("https://apis.roblox.com/marketplace-items/v1/items/details",
                                                                     json={"itemIds": [json_response["collectibleItemId"]]},
                                                                     headers={"x-csrf-token": currentAccount["xcsrf_token"], 'Accept': "application/json"},
                                                                     cookies={".ROBLOSECURITY": currentAccount["cookie"]}, ssl=False)
                            response.raise_for_status()
                            productid_data = json.loads(await productid_response.text())[0]
                            
                            coroutines = [self.buy_item(item_id = json_response["collectibleItemId"], price = json_response['price'], user_id = self.accounts[i]["id"], creator_id = json_response['creatorTargetId'], product_id = productid_data['collectibleProductId'], cookie = self.accounts[i]["cookie"], x_token = self.accounts[i]["xcsrf_token"], raw_id = id) for i in self.accounts for _ in range(4)]
                            self.task = "Item Buyer"
                            await asyncio.gather(*coroutines)
                        else:
                            if json_response.get('unitsAvailableForConsumption', 1) == 0:
                                    del self.items[id]
                                    del self.tasks[id]
                                    for item in self.config["items"]:
                                        if item["id"] == id:
                                            self.config["items"].remove(item)
                                            break
                
                                    with open('config.json', 'w') as f:
                                        json.dump(self.config, f, indent=4)
                                    return
                                
                    t1 = asyncio.get_event_loop().time()
                    self.last_time = round(t1 - t0, 3) 
        except aiohttp.ClientConnectorError as e:
            print(f'Connection error: {e}')
            self.errors += 1
        except aiohttp.ContentTypeError as e:
            print(f'Content type error: {e}')
            self.errors += 1
        except aiohttp.ClientResponseError as e:
            status_code = int(str(e).split(',')[0])
            if status_code == 429:
                await asyncio.to_thread(logging.info, "Rate limit hit")
                await asyncio.sleep(1.5)
            pass
        except asyncio.CancelledError:
            return
        except asyncio.TimeoutError as e:
            print(f"Timeout error: {e}")
            self.errors += 1
        finally:
            self.checks += 1
            await asyncio.sleep(self.wait_time(id, proxy = True if self.proxies is not None and len(self.proxies) > 0 else False))
            
                               
    async def given_id_sniper(self) -> None:
     self.task = "Item Scraper & Searcher"
     async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=None)) as session:
      for current in self.items:
         self.tasks[current] = asyncio.create_task(self.search(session=session, id=current))
      await asyncio.gather(*self.tasks.values())
          
    async def start(self):
            await asyncio.to_thread(logging.info, "Started sniping")
            coroutines = []
            coroutines.append(self.given_id_sniper())
            # coroutines.append(self.auto_search())
            coroutines.append(self.auto_update())
            coroutines.append(self.auto_xtoken())
            await asyncio.gather(*coroutines)
    
    async def auto_xtoken(self):
        while True:
            await asyncio.sleep(5)
            if not await self._check_xcsrf_token():
                raise Exception("x_csrf_token couldn't be generated")
            
    async def auto_update(self):
        while True:
            os.system(self.clear)
            self._print_stats()
            await asyncio.sleep(self.themeWaitTime)
            
 sniper = Sniper()
except Exception as e:
    logging.error(f"An error occurred: {traceback.format_exc()}")
    print("File crashed. Logs have been saved in logs.txt")
    os.system("pause")