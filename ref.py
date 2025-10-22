# 1. 基本使用
from wxauto import WeChat

# 初始化微信实例
wx = WeChat()

# 发送消息
wx.SendMsg("你好", who="张三")

# 获取当前聊天窗口消息
msgs = wx.GetAllMessage()
for msg in msgs:
    print(f"消息内容: {msg.content}, 消息类型: {msg.type}")


# 2. 监听消息
from wxauto import WeChat
from wxauto.msgs import FriendMessage
import time

wx = WeChat()

# 消息处理函数
def on_message(msg, chat):
    text = f'[{msg.type} {msg.attr}]{chat} - {msg.content}'
    print(text)
    with open('msgs.txt', 'a', encoding='utf-8') as f:
        f.write(text + '\n')

    if msg.type in ('image', 'video'):
        print(msg.download())

    if isinstance(msg, FriendMessage):
        time.sleep(len(msg.content))
        msg.quote('收到')

    ...# 其他处理逻辑，配合Message类的各种方法，可以实现各种功能

# 添加监听，监听到的消息用on_message函数进行处理
wx.AddListenChat(nickname="张三", callback=on_message)

# ... 程序运行一段时间后 ...

# 移除监听
wx.RemoveListenChat(nickname="张三")