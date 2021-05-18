import requests,random,os,json, re, filetype
from hoshino import Service,R,priv, aiorequests
from hoshino.config import RES_DIR
from hoshino.typing import CQEvent
from hoshino.util import DailyNumberLimiter
import hoshino

sv_help = '''
[今天吃什么] 看看今天吃啥
'''.strip()

sv = Service(
    name = '今天吃什么',  #功能名
    use_priv = priv.NORMAL, #使用权限   
    manage_priv = priv.ADMIN, #管理权限
    visible = True, #可见性
    enable_on_default = True, #默认启用
    bundle = '娱乐', #分组归类
    help_ = sv_help #帮助说明
    )

_day_limit = 5
_lmt = DailyNumberLimiter(_day_limit)

def get_foods():
    if os.path.exists(os.path.join(os.path.dirname(__file__), 'foods.json')):
        with open(os.path.join(os.path.dirname(__file__), 'foods.json'),"r",encoding='utf-8') as dump_f:
            try:
                words = json.load(dump_f)
            except Exception as e:
                hoshino.logger.error(f'读取食谱时发生错误{type(e)}')
                return None
    else:
        hoshino.logger.error(f'目录下未找到食谱')
    keys = list(words.keys())
    key = random.choice(keys)
    return words[key]

@sv.on_rex(r'^(今天|[早中午晚][上饭餐午]|夜宵)吃(什么|啥|点啥)')
async def net_ease_cloud_word(bot,ev:CQEvent):
    uid = ev.user_id
    if not _lmt.check(uid):
        return
    match = ev.match
    time = match.group(1).strip()
    food = get_foods()
    to_eat = f'{time}去吃{food["name"]}吧~'
    try:
        if "pic" in food:
            foodimg = str(R.img(f'foods/{food["pic"]}').cqcode)
        else:
            foodimg = str(R.img(f'foods/{food["name"]}.jpg').cqcode)
        to_eat = to_eat+foodimg
    except Exception as e:
        hoshino.logger.error(f'读取食物图片时发生错误{type(e)}')
    await bot.send(ev, to_eat, at_sender=True)
    _lmt.increase(uid)

                                
async def download_async(url: str, save_path: str, save_name: str, auto_extension=False):
    resp= await aiorequests.get(url, stream=True)
    if resp.status_code == 404:
        raise ValueError('文件不存在')
    content = await resp.content
    if auto_extension: #没有指定后缀，自动识别后缀名
        try:
            extension = filetype.guess_mime(content).split('/')[1]
        except:
            raise ValueError('不是有效文件类型')
        abs_path = os.path.join(save_path, f'{save_name}.{extension}')
    else:
        abs_path = os.path.join(save_path, save_name)
    with open(abs_path, 'wb') as f:
        f.write(content)
        return abs_path
                                
                                
@sv.on_prefix('添菜')
async def add_food(bot,ev:CQEvent):
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.send(ev,'此命令仅管理员可用~')
        return
    food = ev.message.extract_plain_text().strip()
    ret = re.search(r"\[CQ:image,file=(.*)?,url=(.*)\]", str(ev.message))
    if not ret:
        await bot.send(ev,'请附带美食图片~')
        return
    hash = ret.group(1)
    url = ret.group(2)
    savepath = os.path.join(os.path.expanduser(RES_DIR), 'img', 'foods')
    if not os.path.exists(savepath):
        os.mkdir(savepath)
    imgpath = await download_async(url, savepath, str(food), auto_extension=True)
    pic = os.path.split(imgpath)[1]
    with open(os.path.join(os.path.dirname(__file__), 'foods.json'),"r",encoding='utf-8') as dump_f:
        words = json.load(dump_f)
    words[hash] = {"name":food, "pic":pic}
    with open(os.path.join(os.path.dirname(__file__), 'foods.json'),'w',encoding='utf8') as f:
        json.dump(words, f, ensure_ascii=False,indent=2)
    await bot.send(ev,'食谱已增加~')
