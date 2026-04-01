"""
LMU API connector
Replaces rF2 API connector to use pyLMUSharedMemory natively
"""

import logging
import threading
from time import monotonic

from pyLMUSharedMemory import lmu_data
from pyLMUSharedMemory.lmu_mmap import MMapControl, LMUConstants

logger = logging.getLogger(__name__)

INVALID_INDEX = -1
MAX_VEHICLES = LMUConstants.MAX_MAPPED_VEHICLES

class RF2Info:
    """LMU API data output adapter for BridgeV2"""

    __slots__ = (
        "_access_mode",
        "_updating",
        "_update_thread",
        "_event",
        "mmap_ctrl",
        "paused",
        "player_index",
        "_state_override",
        "_active_state"
    )

    def __init__(self) -> None:
        self._access_mode = 0
        self._updating = False
        self._update_thread = None
        self._event = threading.Event()
        self.mmap_ctrl = MMapControl(LMUConstants.LMU_SHARED_MEMORY_FILE, lmu_data.LMUObjectOut)
        self.paused = True
        self.player_index = INVALID_INDEX
        self._state_override = False
        self._active_state = False

    def start(self) -> None:
        if self._updating:
            return
        self._updating = True
        self.mmap_ctrl.create(self._access_mode)
        self._event.clear()
        self._update_thread = threading.Thread(target=self.__update, daemon=True)
        self._update_thread.start()
        logger.info("LMUSharedMemory: UPDATING started")

    def stop(self) -> None:
        if self._updating:
            self._event.set()
            self._updating = False
            if self._update_thread and self._update_thread.is_alive():
                self._update_thread.join(timeout=1.0)
            self.mmap_ctrl.close()

    def setPID(self, pid: str = "") -> None: pass
    def setMode(self, mode: int = 0) -> None: self._access_mode = mode
    def setStateOverride(self, state: bool = False) -> None: self._state_override = state
    def setActiveState(self, state: bool = False) -> None: self._active_state = state

    def __update(self) -> None:
        self.paused = False
        while not self._event.wait(0.05):
            self.mmap_ctrl.update()
            data = self.mmap_ctrl.data
            if data and data.telemetry.playerHasVehicle:
                self.player_index = data.telemetry.playerVehicleIdx
                self.paused = False
            else:
                self.player_index = INVALID_INDEX
                self.paused = True

    @property
    def rf2ScorInfo(self) -> lmu_data.LMUScoringInfo:
        return self.mmap_ctrl.data.scoring.scoringInfo

    def rf2ScorVeh(self, index: int | None = None) -> lmu_data.LMUVehicleScoring:
        idx = self.player_index if index is None else index
        idx = max(0, min(idx, MAX_VEHICLES - 1))
        return self.mmap_ctrl.data.scoring.vehScoringInfo[idx]

    def rf2TeleVeh(self, index: int | None = None) -> lmu_data.LMUVehicleTelemetry:
        idx = self.player_index if index is None else index
        idx = max(0, min(idx, MAX_VEHICLES - 1))
        return self.mmap_ctrl.data.telemetry.telemInfo[idx]

    @property
    def lmuData(self) -> lmu_data.LMUObjectOut:
        return self.mmap_ctrl.data

    @property
    def playerIndex(self) -> int:
        return self.player_index

    def isPlayer(self, index: int) -> bool:
        return index == self.player_index

    @property
    def isPaused(self) -> bool:
        return self.paused or self.player_index == INVALID_INDEX

    @property
    def isActive(self) -> bool:
        if self._state_override:
            return self._active_state
        return not self.isPaused

    @property
    def identifier(self) -> str:
        return "LMU"