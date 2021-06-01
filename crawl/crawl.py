from bs4 import BeautifulSoup
import urllib
import time
import os
import requests
from selenium import webdriver

sln_options = webdriver.ChromeOptions()
sln_options.add_argument('--headless')
sln_options.add_argument('--no-sandbox')
sln_options.add_argument('--disable-dev-shm-usage')

def soup_page(page):
    try:
      return BeautifulSoup(page, 'lxml')
    except:
      print("Cannot fetch the requested page")

# Open album page
url_input = 'https://imsports.vn/giai-chay-nam-2021-ac1925.html'
albums_page = urllib.request.urlopen(url_input)
soup = soup_page(albums_page)
# Locate albums section and retrieve all album links
lastpage = soup.find('a', attrs={'class': 'paging-last'})
find_all_list = soup.find_all('h3', attrs={'class': 'product-name'})
albums_lists = []
if lastpage != []:
  x = int(lastpage['href'].split("?page=",1)[1])
  allpaging = []
  for i in range(1,x+1):
    url =  url_input + '?page=%d'%i
    allpaging.append(url)
  for k in range(0,len(allpaging)):
    albums_page = urllib.request.urlopen(allpaging[k])
    soup = soup_page(albums_page)
    albums_list = soup.find_all('h3', attrs={'class': 'product-name'})
    albums_lists = albums_lists + albums_list
else: 
  albums_lists = find_all_list
for x in range(len(albums_lists)):
  albums_lists[x] = albums_lists[x].find('a')
albums_pages = []
for l in albums_lists:
  albums_pages.append('https://imsports.vn'+l['href'])
print('{} albums found.'.format(len(albums_pages)))

def load_page(url):
    driver = webdriver.Chrome('/home/tuta/test/crawl/chromedriver', options=sln_options)
    driver.get(url)
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
      driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
      time.sleep(1.0)
      new_height = driver.execute_script("return document.body.scrollHeight")
      if new_height == last_height:
        break
      last_height = new_height
    return driver

a_num=0
for album in albums_pages:
  photo_page = load_page(album)
  a_num+=1
  # Retrieve content of the album
  soup = soup_page(photo_page.page_source)
  photo_list = soup.find_all('div', attrs={'class': 'itemImgGll'})
  for y in range(0, len(photo_list)):
    photo_list[y] = photo_list[y].find('a')
  print('Album {} contains {} photos.'.format(a_num, len(photo_list)))
  # # Download photos from an album
  for i in photo_list:
    lnk = i['href']
    print(lnk)
  #   print(lnk)
  #   with open(img_path + os.path.basename(lnk), "wb") as f:
  #     f.write(requests.get(lnk).content)
  # print('Finished processing album {}'.format(a_num))

