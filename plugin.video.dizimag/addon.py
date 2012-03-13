# Licensed under the GNU General Public License, version 2.
# See the file http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import xbmc, xbmcaddon, xbmcgui, xbmcplugin
import urllib, urlparse, urllib2, sys, re, xml.dom.minidom as md

SHOWNAMES_URL = "http://i.dizimag.com/cache/d.js"
SHOWFLV_URL = "http://www.dizimag.com/_list.asp?dil=1&x=%(code)s&d.xml"
SHOW_URL = "http://www.dizimag.com/%(show)s"
SHOW_THUMBNAIL_URL = "http://i.dizimag.com/dizi/%(show)s.jpg"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:10.0.1) Gecko/20100101 Firefox/10.0.1"

WATCH_SHOW_TR_SUB_HD_URL = "http://www.dizimag.com/%(show)s-%(season)s-sezon-%(episode)s-bolum-720p-izle-dizi.html"
WATCH_SHOW_TR_SUB_URL = "http://www.dizimag.com/%(show)s-%(season)s-sezon-%(episode)s-bolum-izle-dizi.html"
WATCH_SHOW_ENG_SUB_URL = "http://www.dizimag.com/%(show)s-%(season)s-sezon-%(episode)s-bolum-subing-izle-dizi.html"
WATCH_SHOW_NO_SUB_URL = "http://www.dizimag.com/%(show)s-%(season)s-sezon-%(episode)s-bolum-nosub-izle-dizi.html"

# poor man's enum, hehe
# Be careful: Types are in the order of choice
WATCH_TYPE_TR_SUB_HD, WATCH_TYPE_TR_SUB, WATCH_TYPE_ENG_SUB, WATCH_TYPE_NO_SUB, = range(4)

WATCH_URL = { WATCH_TYPE_TR_SUB_HD: (WATCH_SHOW_TR_SUB_HD_URL, "720p HD video"), 
              WATCH_TYPE_TR_SUB:    (WATCH_SHOW_TR_SUB_URL,     "Low resolution video with Turkish subtitles"),
              WATCH_TYPE_ENG_SUB:   (WATCH_SHOW_ENG_SUB_URL,    "Low resolution video with English subtitles"),  
              WATCH_TYPE_NO_SUB:    (WATCH_SHOW_NO_SUB_URL,     "Low resolution video")} 

__plugin__ = 'Dizimag'
__author__ = 'Gokcen Eraslan <gokcen.eraslan@gmail.com>'
__url__ = 'http://code.google.com/p/plugin/'
__date__ = '03-14-2012'
__version__ = '0.2.0'
__settings__ = xbmcaddon.Addon( id = 'plugin.video.dizimag' )

PLUGIN_ID = int(sys.argv[1])


playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
player = xbmc.Player( xbmc.PLAYER_CORE_MPLAYER )

def open_url(url):
    #print url
    try:
        req = urllib2.Request( url )
        req.add_header('User-Agent', USER_AGENT)
        content = urllib2.urlopen( req )
    except urllib2.HTTPError:
        #print "URL (%s) not found..." % url
        return None

    data = content.read()
    content.close()
    return data

def get_show_names():
    djs = open_url(SHOWNAMES_URL)

    if not djs:
        print 'Page not found...'
        return
        
    show_names = re.findall(r'd: \"(.*?)\", s: \"(.*?)\"', djs)
    return show_names

def get_show_thumbnail_url(showcode):
    return SHOW_THUMBNAIL_URL % {'show': showcode}

def get_show_episode_info(showcode):
    showpage = open_url(SHOW_URL % {'show': showcode})

    if not showpage:
        print "No such page exists..."
        return

    episode_urls = re.findall(r'href="/%s-(\d+?)-sezon-(\d+?)-bolum-[a-zA-Z0-9-]*?izle-dizi\.html"' % (showcode), showpage)
    return sorted(list(set(episode_urls)), cmp = lambda x,y: cmp(int(x[0])*1000+int(x[1]), int(y[0])*1000+int(y[1])), reverse=True)

def parse_show_rss(rss):
    tree = md.parseString(rss)

    video_urls = filter(lambda x: x, (x.getAttribute("url") for x in tree.getElementsByTagName("media:content")))
    video_thumbnails = filter(lambda x: x, (x.getAttribute("url") for x in tree.getElementsByTagName("media:thumbnail")))

    return (video_urls, video_thumbnails)

def get_show_video_urls(showcode, season, episode, watch_type = WATCH_TYPE_TR_SUB_HD):

    def get_show(t):

        showpage = open_url(WATCH_URL[t][0] % {'show': showcode, 'season': season, 'episode': episode})

        if not showpage:
            return

        lowres = re.search(r'dusuk="(.*?)";', showpage)
        highres = re.search(r'yuksek="(.*?)";', showpage)

        if lowres:
            lowres = lowres.group(1)
        if highres:
            highres = highres.group(1)

        if not (highres or lowres):
            return

        rss = open_url(SHOWFLV_URL % {'code': highres})

        if not rss:
            rss = open_url(SHOWFLV_URL % {'code': lowres})
            if not rss:
                return

        video_urls, video_thumbnails = parse_show_rss(rss)
        if not video_urls:
            return

        return video_urls, video_thumbnails


    show = get_show(watch_type)

    if not show or not show[0]:
        print "This episode is not available in format: '%s'" % WATCH_URL[watch_type][1]

        for fallback in sorted(WATCH_URL.keys()):
            if fallback == watch_type:
                continue # tried before

            show = get_show(fallback)
            if show and show[0]:
                break

            else:
                print "This episode is not available in format: '%s'" % WATCH_URL[fallback][1]

        else:
            print "This episode is not available in any format."
            return

    return show

def test():
    for s in get_show_names():
        print "*   Getting info for '%s'..." % s[0].decode("iso-8859-9")
        info = get_show_episode_info(s[1])
        for ses, ep in info:
            print get_show_video_urls(s[1], ses, ep)
            print "*********************************"

    print get_show_video_urls("how-i-met-your-mother", "3", "3", WATCH_TYPE_TR_SUB)
    print get_show_video_urls("spartacus-vengeance", "2", "1")
    get_show_episode_info("spartacus-vengeance")


#### PLUGIN STUFF ####

def display_mainmenu():
    shownames = get_show_names()
    for name, code in shownames:
        name = name.decode("iso-8859-9").encode("utf-8")
        thumbimage = get_show_thumbnail_url(code)
        create_list_item(name, create_xbmc_url(action="showSeasons", name=name, showcode=code))
        #create_list_item(name, create_xbmc_url(action="showEpisodes", name=name, showcode=code), thumbnailImage=thumbimage)

    xbmcplugin.endOfDirectory(PLUGIN_ID)

def display_show_seasons(params):
    name = params["name"][0]
    code = params["showcode"][0]

    thumbimage = get_show_thumbnail_url(code)

    epinfo = get_show_episode_info(code)
    seasonSet = list(set([int(x[0]) for x in epinfo]))
    seasonStringWidth = len(str(max(seasonSet)))

    for s in sorted(seasonSet, reverse = True):
        create_list_item("%s - Season %s" % (name, str(s).zfill(seasonStringWidth)), create_xbmc_url(action="showEpisodes", name=name, showcode=code, season=s), thumbnailImage = thumbimage)

    xbmcplugin.endOfDirectory(PLUGIN_ID)
   
def display_show_episodes(params):
    name = params["name"][0]
    code = params["showcode"][0]
    season = params["season"][0]
    
    thumbimage = get_show_thumbnail_url(code)

    epinfo = get_show_episode_info(code)
    eplist = list(set((int(x[1]) for x in epinfo if x[0] == season)))
    episodeStringWidth = len(str(max(eplist)))

    for e in sorted(eplist, reverse = True):
        create_list_item("%s - S%sE%s" % (name,season,str(e).zfill(episodeStringWidth)), create_xbmc_url(action="showVideo", name=name, showcode=code, season=season, episode=str(e)), thumbnailImage = thumbimage)

    xbmcplugin.endOfDirectory(PLUGIN_ID)

def display_show(params):
    name = params["name"][0]
    code = params["showcode"][0]
    season = params["season"][0]
    episode = params["episode"][0]

    urls = get_show_video_urls(code, season, episode)
    iconImage = thumb = get_show_thumbnail_url(code)

    if not urls:
        dia = xbmcgui.Dialog()
        dia.ok("Error", "Episode not found...")
        return


    video_urls, video_thumbnails = urls
    if video_thumbnails:
        iconImage = video_thumbnails[0]

    """
    for i, video in enumerate(video_urls):
        create_list_item("Part %s" % (i+1), video, iconImage = iconImage, thumbnailImage = thumb, folder = False)
    xbmcplugin.endOfDirectory(PLUGIN_ID)
    """

    playlist.clear()
    for i, video in enumerate(video_urls):
        listitem = xbmcgui.ListItem('Episode %s Part %s' % (episode, (i+1)))
        listitem.setInfo('video', {'Title': name})
        playlist.add(url=video, listitem=listitem)

    player.play(playlist)

def create_xbmc_url(**parameters):
    return "%s?%s" % (sys.argv[0], urllib.urlencode(parameters))

def create_list_item(name, url, iconImage = "", thumbnailImage = "", folder = True):
    if folder and not iconImage:
        iconImage = "DefaultFolder.png"
    elif not folder and not iconImage:
        iconImage = "DefaultVideo.png"

    l = xbmcgui.ListItem(name, iconImage = iconImage, thumbnailImage = thumbnailImage )
    l.setInfo( type = "Video", infoLabels = { "Title": name } ) 
    xbmcplugin.addDirectoryItem(handle=PLUGIN_ID, url = url, listitem = l, isFolder = folder)


ACTION_HANDLERS = { "showEpisodes": display_show_episodes,
                    "showSeasons" : display_show_seasons,
                    "showVideo"   : display_show }

params = urlparse.parse_qs(sys.argv[2][1:])

if len(params) == 0:
    display_mainmenu()
else:
    ACTION_HANDLERS[params['action'][0]](params)