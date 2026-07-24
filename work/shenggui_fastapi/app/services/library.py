from __future__ import annotations


DIALECT_LIBRARY: dict[str, dict[str, dict[str, str]]] = {
    "yue": {
        "market": {
            "name": "菜场生存",
            "target_text": "阿姐，呢个番茄点卖呀？帮我称两斤。",
            "focus": "询价、称重、还价、寒暄收尾",
        },
        "family": {
            "name": "亲戚社交",
            "target_text": "姑妈，好耐冇见，最近身子点呀？",
            "focus": "称呼、问候、回应关心、礼貌转移",
        },
        "office": {
            "name": "职场防御",
            "target_text": "呢件事我今晚未必赶得切，我先同你确认下重点。",
            "focus": "委婉拒绝、确认边界、快速复述",
        },
    },
    "wu": {
        "market": {
            "name": "菜场生存",
            "target_text": "阿姐，搿个番茄几钿一斤？帮我称两斤。",
            "focus": "询价、称重、还价、寒暄收尾",
        },
        "family": {
            "name": "亲戚社交",
            "target_text": "阿姨，好久勿见，近来身体好伐？",
            "focus": "称呼、问候、回应关心、礼貌转移",
        },
        "office": {
            "name": "职场防御",
            "target_text": "搿件事我今朝未必来得及，我先搭侬确认重点。",
            "focus": "委婉拒绝、确认边界、快速复述",
        },
    },
    "southwest": {
        "market": {
            "name": "菜场生存",
            "target_text": "嬢嬢，这个番茄好多钱一斤嘛？帮我称两斤。",
            "focus": "询价、称重、还价、寒暄收尾",
        },
        "family": {
            "name": "亲戚社交",
            "target_text": "嬢嬢，好久没看到你了，最近身体还可以噻？",
            "focus": "称呼、问候、回应关心、礼貌转移",
        },
        "office": {
            "name": "职场防御",
            "target_text": "这个事我今晚不一定赶得拢，我先跟你确认哈重点。",
            "focus": "委婉拒绝、确认边界、快速复述",
        },
    },
}

SCENE_LIBRARY = DIALECT_LIBRARY["yue"]


def get_scene_data(dialect: str, scene: str) -> dict[str, str]:
    scene_library = DIALECT_LIBRARY.get(dialect, SCENE_LIBRARY)
    return scene_library.get(scene, scene_library["market"])
