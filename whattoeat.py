import hoshino, random, os, re, filetype
from hoshino import Service, R, priv, aiorequests
from hoshino.config import RES_DIR
from hoshino.typing import CQEvent
from hoshino.util import DailyNumberLimiter

sv_help = '''
[今天吃什么] 看看今天吃啥
[添菜 菜名] +美食图片 添加新菜品
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

_lmt = DailyNumberLimiter(5)
imgpath = os.path.join(os.path.expanduser(RES_DIR), 'img', 'foods')

@sv.on_rex(r'^(今天|[早中午晚][上饭餐午]|夜宵)吃(什么|啥|点啥)')
async def what_to_eat(bot, ev: CQEvent):
    uid = ev.user_id
    if not _lmt.check(uid):
        await bot.finish(ev, '你今天吃的已经够多的了！', at_sender=True)
    match = ev['match']
    time = match.group(1).strip()
    food = random.choice(os.listdir(imgpath))
    name = food.split('.')
    to_eat = f'{time}去吃{name[0]}吧~\n'
    try:
        foodimg = R.img(f'foods/{food}').cqcode
        to_eat += str(foodimg)
    except Exception as e:
        hoshino.logger.error(f'读取食物图片时发生错误{type(e)}')
    await bot.send(ev, to_eat, at_sender=True)
    _lmt.increase(uid)

async def download_async(url: str, name: str):
    resp = await aiorequests.get(url, stream=True)
    if resp.status_code != 200:
        raise ValueError(f'图片下载失败（HTTP {resp.status_code}）')
    content = await resp.content
    try:
        extension = filetype.guess_mime(content).split('/')[1]
    except:
        raise ValueError('不是有效文件类型')
    abs_path = os.path.join(imgpath, f'{name}.{extension}')
    with open(abs_path, 'wb') as f:
        f.write(content)

@sv.on_prefix(('添菜','添加菜品'))
@sv.on_suffix(('添菜','添加菜品'))
async def add_food(bot, ev: CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        return
    food = ev.message.extract_plain_text().strip()
    # 与 __init__.py / util.py 一致：遍历消息段判断图片，
    # 而不是用正则匹配 str(ev.message)（接收到的图片 CQ 码不一定带 url 字段）
    img_seg = next((ms for ms in ev.message if ms['type'] == 'image'), None)
    if not img_seg:
        await bot.send(ev,'请附带美食图片~')
        return
    # 与 util.ms_handler_image 一致：优先取 url，缺省回退到 file
    url = str(img_seg['data'].get('url') or img_seg['data'].get('file') or '').strip()
    if not url:
        await bot.send(ev,'请附带美食图片~')
        return
    if not food or not food.strip('.'):
        await bot.send(ev,'请给菜品起个名字~')
        return
    if re.search(r'[\\/:*?"<>|\x00-\x1f]', food):
        await bot.send(ev,'菜名里混入了无法使用的字符，换一个吧~')
        return
    if len(food) > 60:
        await bot.send(ev,'菜名太长了（60 字以内），换一个吧~')
        return
    try:
        await download_async(url, food)
    except ValueError as e:
        await bot.send(ev, f'添加失败：{e}')
        return
    except Exception as e:
        hoshino.logger.error(f'添菜下载失败 {type(e)}: {e}')
        await bot.send(ev, '添加失败，图片可能暂时取不到，稍后再试试吧~')
        return
    await bot.send(ev,'食谱已增加~')
