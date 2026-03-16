from typing import Dict, Type, List, Any
from ui.modules.base_module import BaseModule
from ui.modules.kun28_panel import Kun28Panel
from ui.modules.soul_king_panel import SoulKingPanel
# 未来添加新功能只需在这里导入
from ui.modules.realm_raid_panel import RealmRaidPanel
from ui.modules.event_tower_panel import EventTowerPanel
from ui.modules.huijuan_panel import ShuaHuajuanPanel

class ModuleFactory:
    """
    简单工厂模式 (Simple Factory)
    负责注册和实例化所有的业务模块。
    """
    _REGISTRY: Dict[str, Type[BaseModule]] = {
        "困28": Kun28Panel,
        "魂王": SoulKingPanel,
        # 新功能在此处注册，例如: "御灵": YuLingPanel
        "结界突破": RealmRaidPanel,
        "活动爬塔": EventTowerPanel,
        "绘卷": ShuaHuajuanPanel,
    }

    @classmethod
    def get_available_modules(cls) -> List[str]:
        """获取所有已注册的功能名称列表"""
        return list(cls._REGISTRY.keys())

    @classmethod
    def create_module(cls, module_name: str, main_frame: Any, game_window: Any) -> BaseModule:
        """根据名称创建模块实例"""
        module_cls = cls._REGISTRY.get(module_name)
        if not module_cls:
            raise ValueError(f"未知的模块名称: {module_name}")
        return module_cls(main_frame, game_window)