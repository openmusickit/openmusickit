from typing import Tuple, Iterable
from openmusickit.time.duration import TemporalUnit, CompoundTemporalUnit

class TimeSignature(CompoundTemporalUnit):

    def __init__(self, spec: TemporalUnit|Iterable[TemporalUnit]|CompoundTemporalUnit,
                 presentation: Tuple[str, str]=None):
        
        if isinstance(spec, TemporalUnit):
            spec = [spec,]
        if isinstance(spec, CompoundTemporalUnit):
            spec = CompoundTemporalUnit._units
        
        super().__init__(spec)

        self._presentation = presentation

    @property
    def spec(self):
        return self._units
    
    @property
    def n(self):
        if self._presentation:
            return self._presentation[0]
        return None
        
    @property
    def d(self):
        if self._presentation:
            return self._presentation[1]
        return None


    def __repr__(self):
        if self._presentation:
            return f"TimeSignature({self._units!r}, {self._presentation})"
        else:
            return f"TimeSignature({self._units!r}"