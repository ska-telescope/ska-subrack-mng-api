from reprlib import recursive_repr
# Purely functional, no descriptor behaviour
class partial:
    """New function with partial application of the given arguments
    and keywords.
    """

    __slots__ = "func", "args", "keywords", "__dict__", "__weakref__"

    def __new__(cls, func, /, *args, **keywords):
        if not callable(func):
            raise TypeError("the first argument must be callable")

        if hasattr(func, "func"):
            args = func.args + args
            keywords = {**func.keywords, **keywords}
            func = func.func

        self = super(partial, cls).__new__(cls)

        self.func = func
        self.args = args
        self.keywords = keywords
        return self

    def __call__(self, /, *args, **keywords):
        keywords = {**self.keywords, **keywords}
        return self.func(*self.args, *args, **keywords)

    @recursive_repr()
    def __repr__(self):
        qualname = type(self).__qualname__
        args = [repr(self.func)]
        args.extend(repr(x) for x in self.args)
        args.extend(f"{k}={v!r}" for (k, v) in self.keywords.items())
        if type(self).__module__ == "functools":
            return f"functools.{qualname}({', '.join(args)})"
        return f"{qualname}({', '.join(args)})"

    def __reduce__(self):
        return type(self), (self.func,), (self.func, self.args,
               self.keywords or None, self.__dict__ or None)

    def __setstate__(self, state):
        if not isinstance(state, tuple):
            raise TypeError("argument to __setstate__ must be a tuple")
        if len(state) != 4:
            raise TypeError(f"expected 4 items in state, got {len(state)}")
        func, args, kwds, namespace = state
        if (not callable(func) or not isinstance(args, tuple) or
           (kwds is not None and not isinstance(kwds, dict)) or
           (namespace is not None and not isinstance(namespace, dict))):
            raise TypeError("invalid partial state")

        args = tuple(args) # just in case it's a subclass
        if kwds is None:
            kwds = {}
        elif type(kwds) is not dict: # XXX does it need to be *exactly* dict?
            kwds = dict(kwds)
        if namespace is None:
            namespace = {}

        self.__dict__ = namespace
        self.func = func
        self.args = args
        self.keywords = kwds

def _exp_value(nominal, tolerance_perc):
    return {'min': round(nominal*(1-tolerance_perc/100),2),'max': round(nominal*(1+tolerance_perc/100),2)}

def load_subrack_lookup(obj):
    return{
        'temperatures' : {
            'SMM1'   : {'method': partial(obj.Mng.GetMngTemp, sens_id = 1),      'group' : 'temperatures', 'exp_value': { 'min': 10.00, 'max': 50.00}, 'unit' : '°C'},
            'SMM2'   : {'method': partial(obj.Mng.GetMngTemp, sens_id = 2),      'group' : 'temperatures', 'exp_value': { 'min': 10.00, 'max': 50.00}, 'unit' : '°C'},
            'BKPLN1' : {'method': partial(obj.Bkpln.get_sens_temp, sens_id = 1, ret_val_only = True), 'group' : 'temperatures', 'exp_value': { 'min': 10.00, 'max': 50.00}, 'unit' : '°C'},
            'BKPLN2' : {'method': partial(obj.Bkpln.get_sens_temp, sens_id = 2, ret_val_only = True), 'group' : 'temperatures', 'exp_value': { 'min': 10.00, 'max': 50.00}, 'unit' : '°C'},
        },
        'plls' : {
            'BoardPllLock' : {'method': obj.GetLockedPLL,     'group' : 'plls', 'exp_value': { 'min': True, 'max': True}, 'unit' : ''},
            'CPLDPllLock'  : {'method': obj.GetCPLDLockedPLL, 'group' : 'plls', 'exp_value': { 'min': True, 'max': True}, 'unit' : ''},
            'PllSource'    : {'method': obj.GetPllSource,     'group' : 'plls', 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
        },
        'fans' : {
            'speed' : {
                'FAN1'   : {'method': partial(obj.GetFanRpm, fan_id = 1), 'group' : ['fans', 'FAN1'], 'exp_value': { 'min': None, 'max': None}, 'unit' : 'rpm'},
                'FAN2'   : {'method': partial(obj.GetFanRpm, fan_id = 2), 'group' : ['fans', 'FAN2'], 'exp_value': { 'min': None, 'max': None}, 'unit' : 'rpm'},
                'FAN3'   : {'method': partial(obj.GetFanRpm, fan_id = 3), 'group' : ['fans', 'FAN3'], 'exp_value': { 'min': None, 'max': None}, 'unit' : 'rpm'},
                'FAN4'   : {'method': partial(obj.GetFanRpm, fan_id = 4), 'group' : ['fans', 'FAN4'], 'exp_value': { 'min': None, 'max': None}, 'unit' : 'rpm'},
            },
            'pwm_duty' : {
                'FAN1'   : {'method': partial(obj.GetFanPwm, fan_id = 1), 'group' : ['fans', 'FAN1'], 'exp_value': { 'min': None, 'max': None}, 'unit' : '%'},
                'FAN2'   : {'method': partial(obj.GetFanPwm, fan_id = 2), 'group' : ['fans', 'FAN2'], 'exp_value': { 'min': None, 'max': None}, 'unit' : '%'},
                'FAN3'   : {'method': partial(obj.GetFanPwm, fan_id = 3), 'group' : ['fans', 'FAN3'], 'exp_value': { 'min': None, 'max': None}, 'unit' : '%'},
                'FAN4'   : {'method': partial(obj.GetFanPwm, fan_id = 4), 'group' : ['fans', 'FAN4'], 'exp_value': { 'min': None, 'max': None}, 'unit' : '%'},
            },
            'mode' : {
                'FAN1'   : {'method': partial(obj.GetFanMode, fan_id = 1), 'group' : ['fans', 'FAN1'], 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
                'FAN2'   : {'method': partial(obj.GetFanMode, fan_id = 2), 'group' : ['fans', 'FAN2'], 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
                'FAN3'   : {'method': partial(obj.GetFanMode, fan_id = 3), 'group' : ['fans', 'FAN3'], 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
                'FAN4'   : {'method': partial(obj.GetFanMode, fan_id = 4), 'group' : ['fans', 'FAN4'], 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
            },
            
        },
        'psus': {
            'present' : {
                'PSU1'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'present', ps_id = 1), 'group' : ['psus', 'status', 'PSU1'], 'exp_value': { 'min': True, 'max': True}, 'unit' : 'V'},
                'PSU2'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'present', ps_id = 2), 'group' : ['psus', 'status', 'PSU2'], 'exp_value': { 'min': True, 'max': True}, 'unit' : 'V'},
            },
            'busy' : {
                'PSU1'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'busy', ps_id = 1), 'group' : ['psus', 'status', 'PSU1'], 'exp_value': { 'min': None, 'max': None}, 'unit' : 'V'},
                'PSU2'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'busy', ps_id = 2), 'group' : ['psus', 'status', 'PSU2'], 'exp_value': { 'min': None, 'max': None}, 'unit' : 'V'},
            },
            'off' : {
                'PSU1'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'off', ps_id = 1), 'group' : ['psus', 'status', 'PSU1'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
                'PSU2'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'off', ps_id = 2), 'group' : ['psus', 'status', 'PSU2'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
            },
            'vout_ov_fault' : {
                'PSU1'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'vout_ov_fault', ps_id = 1), 'group' : ['psus', 'status', 'PSU1'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
                'PSU2'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'vout_ov_fault', ps_id = 2), 'group' : ['psus', 'status', 'PSU2'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
            },
            'iout_oc_fault' : {
                'PSU1'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'iout_oc_fault', ps_id = 1), 'group' : ['psus', 'status', 'PSU1'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
                'PSU2'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'iout_oc_fault', ps_id = 2), 'group' : ['psus', 'status', 'PSU2'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
            },
            'vin_uv_fault' : {
                'PSU1'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'vin_uv_fault', ps_id = 1), 'group' : ['psus', 'status', 'PSU1'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
                'PSU2'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'vin_uv_fault', ps_id = 2), 'group' : ['psus', 'status', 'PSU2'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
            },
            'temp_fault' : {
                'PSU1'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'temp_fault', ps_id = 1), 'group' : ['psus', 'status', 'PSU1'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
                'PSU2'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'temp_fault', ps_id = 2), 'group' : ['psus', 'status', 'PSU2'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
            },
            'cml_fault' : {
                'PSU1'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'cml_fault', ps_id = 1), 'group' : ['psus', 'status', 'PSU1'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
                'PSU2'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'cml_fault', ps_id = 2), 'group' : ['psus', 'status', 'PSU2'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
            },
            'vout_fault' : {
                'PSU1'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'vout_fault', ps_id = 1), 'group' : ['psus', 'status', 'PSU1'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
                'PSU2'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'vout_fault', ps_id = 2), 'group' : ['psus', 'status', 'PSU2'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
            },
            'iout_fault' : {
                'PSU1'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'iout_fault', ps_id = 1), 'group' : ['psus', 'status', 'PSU1'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
                'PSU2'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'iout_fault', ps_id = 2), 'group' : ['psus', 'status', 'PSU2'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
            },
            'input_fault' : {
                'PSU1'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'input_fault', ps_id = 1), 'group' : ['psus', 'status', 'PSU1'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
                'PSU2'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'input_fault', ps_id = 2), 'group' : ['psus', 'status', 'PSU2'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
            },
            'pwr_gd' : {
                'PSU1'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'pwr_gd', ps_id = 1), 'group' : ['psus', 'status', 'PSU1'], 'exp_value': { 'min': True, 'max': True}, 'unit' : 'V'},
                'PSU2'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'pwr_gd', ps_id = 2), 'group' : ['psus', 'status', 'PSU2'], 'exp_value': { 'min': True, 'max': True}, 'unit' : 'V'},
            },
            'fan_fault' : {
                'PSU1'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'fan_fault', ps_id = 1), 'group' : ['psus', 'status', 'PSU1'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
                'PSU2'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'fan_fault', ps_id = 2), 'group' : ['psus', 'status', 'PSU2'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
            },
            'other' : {
                'PSU1'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'other', ps_id = 1), 'group' : ['psus', 'status', 'PSU1'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
                'PSU2'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'other', ps_id = 2), 'group' : ['psus', 'status', 'PSU2'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
            },
            'unknown' : {
                'PSU1'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'unknown', ps_id = 1), 'group' : ['psus', 'status', 'PSU1'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
                'PSU2'   : {'method': partial(obj.Bkpln.get_ps_status, key = 'unknown', ps_id = 2), 'group' : ['psus', 'status', 'PSU2'], 'exp_value': { 'min': False, 'max': False}, 'unit' : 'V'},
            },
            'voltages' : {
                'PSU1'   : {'method': partial(obj.GetPSVout, ps_id = 1), 'group' : ['psus', 'voltages', 'PSU1'], 'exp_value': _exp_value(12,5), 'unit' : 'V'},
                'PSU2'   : {'method': partial(obj.GetPSVout, ps_id = 2), 'group' : ['psus', 'voltages', 'PSU2'], 'exp_value': _exp_value(12,5), 'unit' : 'V'},
            },
            'currents' : {
                'PSU1'   : {'method': partial(obj.GetPSIout, ps_id = 1), 'group' : ['psus', 'currents', 'PSU1'], 'exp_value': { 'min': None, 'max': 50}, 'unit' : 'A'},
                'PSU2'   : {'method': partial(obj.GetPSIout, ps_id = 2), 'group' : ['psus', 'currents', 'PSU2'], 'exp_value': { 'min': None, 'max': 50}, 'unit' : 'A'},
            },
            'fan_pwm_override' : {
                'PSU1'   : {'method': partial(obj.GetPSFanSpeed, ps_id = 1), 'group' : ['psus', 'fan_pwm_or', 'PSU1'], 'exp_value': { 'min': None, 'max': None}, 'unit' : 'rpm'},
                'PSU2'   : {'method': partial(obj.GetPSFanSpeed, ps_id = 2), 'group' : ['psus', 'fan_pwm_or', 'PSU2'], 'exp_value': { 'min': None, 'max': None}, 'unit' : 'rpm'},
            },
        },
        'pings' : {
            'pings_CPLD'   : {'method': obj.GetPingCpld, 'group' : ['pings', 'CPLD'], 'exp_value': { 'min' : True, 'max': True}, 'unit' : ''},
        },
        'slots': {
            'presence' : {
                'SLOT1'   : {'method': partial(obj.GetTPMPresent, tpm_slot_id = 1), 'group' : ['slots', 'presence', 'SLOT1'], 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
                'SLOT2'   : {'method': partial(obj.GetTPMPresent, tpm_slot_id = 2), 'group' : ['slots', 'presence', 'SLOT2'], 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
                'SLOT3'   : {'method': partial(obj.GetTPMPresent, tpm_slot_id = 3), 'group' : ['slots', 'presence', 'SLOT3'], 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
                'SLOT4'   : {'method': partial(obj.GetTPMPresent, tpm_slot_id = 4), 'group' : ['slots', 'presence', 'SLOT4'], 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
                'SLOT5'   : {'method': partial(obj.GetTPMPresent, tpm_slot_id = 5), 'group' : ['slots', 'presence', 'SLOT5'], 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
                'SLOT6'   : {'method': partial(obj.GetTPMPresent, tpm_slot_id = 6), 'group' : ['slots', 'presence', 'SLOT6'], 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
                'SLOT7'   : {'method': partial(obj.GetTPMPresent, tpm_slot_id = 7), 'group' : ['slots', 'presence', 'SLOT7'], 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
                'SLOT8'   : {'method': partial(obj.GetTPMPresent, tpm_slot_id = 8), 'group' : ['slots', 'presence', 'SLOT8'], 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
            },
            'on' : {
                'SLOT1'   : {'method': partial(obj.Bkpln.is_tpm_on, tpm_id = 1), 'group' : ['slots', 'on', 'SLOT1'], 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
                'SLOT2'   : {'method': partial(obj.Bkpln.is_tpm_on, tpm_id = 2), 'group' : ['slots', 'on', 'SLOT2'], 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
                'SLOT3'   : {'method': partial(obj.Bkpln.is_tpm_on, tpm_id = 3), 'group' : ['slots', 'on', 'SLOT3'], 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
                'SLOT4'   : {'method': partial(obj.Bkpln.is_tpm_on, tpm_id = 4), 'group' : ['slots', 'on', 'SLOT4'], 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
                'SLOT5'   : {'method': partial(obj.Bkpln.is_tpm_on, tpm_id = 5), 'group' : ['slots', 'on', 'SLOT5'], 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
                'SLOT6'   : {'method': partial(obj.Bkpln.is_tpm_on, tpm_id = 6), 'group' : ['slots', 'on', 'SLOT6'], 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
                'SLOT7'   : {'method': partial(obj.Bkpln.is_tpm_on, tpm_id = 7), 'group' : ['slots', 'on', 'SLOT7'], 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
                'SLOT8'   : {'method': partial(obj.Bkpln.is_tpm_on, tpm_id = 8), 'group' : ['slots', 'on', 'SLOT8'], 'exp_value': { 'min': None, 'max': None}, 'unit' : ''},
            },
            'voltages' : {
                'SLOT1'   : {'method': partial(obj.GetTPMVoltage, tpm_slot_id= 1), 'group' : ['slots', 'voltages', 'SLOT1'], 'exp_value': _exp_value(12,5), 'unit' : 'V'},
                'SLOT2'   : {'method': partial(obj.GetTPMVoltage, tpm_slot_id= 2), 'group' : ['slots', 'voltages', 'SLOT2'], 'exp_value': _exp_value(12,5), 'unit' : 'V'},
                'SLOT3'   : {'method': partial(obj.GetTPMVoltage, tpm_slot_id= 3), 'group' : ['slots', 'voltages', 'SLOT3'], 'exp_value': _exp_value(12,5), 'unit' : 'V'},
                'SLOT4'   : {'method': partial(obj.GetTPMVoltage, tpm_slot_id= 4), 'group' : ['slots', 'voltages', 'SLOT4'], 'exp_value': _exp_value(12,5), 'unit' : 'V'},
                'SLOT5'   : {'method': partial(obj.GetTPMVoltage, tpm_slot_id= 5), 'group' : ['slots', 'voltages', 'SLOT5'], 'exp_value': _exp_value(12,5), 'unit' : 'V'},
                'SLOT6'   : {'method': partial(obj.GetTPMVoltage, tpm_slot_id= 6), 'group' : ['slots', 'voltages', 'SLOT6'], 'exp_value': _exp_value(12,5), 'unit' : 'V'},
                'SLOT7'   : {'method': partial(obj.GetTPMVoltage, tpm_slot_id= 7), 'group' : ['slots', 'voltages', 'SLOT7'], 'exp_value': _exp_value(12,5), 'unit' : 'V'},
                'SLOT8'   : {'method': partial(obj.GetTPMVoltage, tpm_slot_id= 8), 'group' : ['slots', 'voltages', 'SLOT8'], 'exp_value': _exp_value(12,5), 'unit' : 'V'},
            },
            'powers' : {
                'SLOT1'   : {'method': partial(obj.Bkpln.get_power_tpm, tpm_id = 1), 'group' : ['slots', 'powers', 'SLOT1'], 'exp_value': { 'min': 0, 'max': 120}, 'unit' : 'W'},
                'SLOT2'   : {'method': partial(obj.Bkpln.get_power_tpm, tpm_id = 2), 'group' : ['slots', 'powers', 'SLOT2'], 'exp_value': { 'min': 0, 'max': 120}, 'unit' : 'W'},
                'SLOT3'   : {'method': partial(obj.Bkpln.get_power_tpm, tpm_id = 3), 'group' : ['slots', 'powers', 'SLOT3'], 'exp_value': { 'min': 0, 'max': 120}, 'unit' : 'W'},
                'SLOT4'   : {'method': partial(obj.Bkpln.get_power_tpm, tpm_id = 4), 'group' : ['slots', 'powers', 'SLOT4'], 'exp_value': { 'min': 0, 'max': 120}, 'unit' : 'W'},
                'SLOT5'   : {'method': partial(obj.Bkpln.get_power_tpm, tpm_id = 5), 'group' : ['slots', 'powers', 'SLOT5'], 'exp_value': { 'min': 0, 'max': 120}, 'unit' : 'W'},
                'SLOT6'   : {'method': partial(obj.Bkpln.get_power_tpm, tpm_id = 6), 'group' : ['slots', 'powers', 'SLOT6'], 'exp_value': { 'min': 0, 'max': 120}, 'unit' : 'W'},
                'SLOT7'   : {'method': partial(obj.Bkpln.get_power_tpm, tpm_id = 7), 'group' : ['slots', 'powers', 'SLOT7'], 'exp_value': { 'min': 0, 'max': 120}, 'unit' : 'W'},
                'SLOT8'   : {'method': partial(obj.Bkpln.get_power_tpm, tpm_id = 8), 'group' : ['slots', 'powers', 'SLOT8'], 'exp_value': { 'min': 0, 'max': 120}, 'unit' : 'W'},
            },
            'pings' : {
                'SLOT1'   : {'method': partial(obj.GetPingTPM, tpm_slot_id = 1), 'group' : ['slots', 'pings', 'SLOT1'], 'exp_value': { 'min' : True, 'max': True}, 'unit' : ''},
                'SLOT2'   : {'method': partial(obj.GetPingTPM, tpm_slot_id = 2), 'group' : ['slots', 'pings', 'SLOT2'], 'exp_value': { 'min' : True, 'max': True}, 'unit' : ''},
                'SLOT3'   : {'method': partial(obj.GetPingTPM, tpm_slot_id = 3), 'group' : ['slots', 'pings', 'SLOT3'], 'exp_value': { 'min' : True, 'max': True}, 'unit' : ''},
                'SLOT4'   : {'method': partial(obj.GetPingTPM, tpm_slot_id = 4), 'group' : ['slots', 'pings', 'SLOT4'], 'exp_value': { 'min' : True, 'max': True}, 'unit' : ''},
                'SLOT5'   : {'method': partial(obj.GetPingTPM, tpm_slot_id = 5), 'group' : ['slots', 'pings', 'SLOT5'], 'exp_value': { 'min' : True, 'max': True}, 'unit' : ''},
                'SLOT6'   : {'method': partial(obj.GetPingTPM, tpm_slot_id = 6), 'group' : ['slots', 'pings', 'SLOT6'], 'exp_value': { 'min' : True, 'max': True}, 'unit' : ''},
                'SLOT7'   : {'method': partial(obj.GetPingTPM, tpm_slot_id = 7), 'group' : ['slots', 'pings', 'SLOT7'], 'exp_value': { 'min' : True, 'max': True}, 'unit' : ''},
                'SLOT8'   : {'method': partial(obj.GetPingTPM, tpm_slot_id = 8), 'group' : ['slots', 'pings', 'SLOT8'], 'exp_value': { 'min' : True, 'max': True}, 'unit' : ''},
            },
        },
        'internal_voltages': {
            'V_SOC': {'method': partial(obj.Mng.get_monitored_board_supplies, "V_SOC"), 'group': ['internal_voltages', 'voltages'],
                      'exp_value': _exp_value(1.35,3), 'unit': 'V'},
            'V_ARM': {'method': partial(obj.Mng.get_monitored_board_supplies, "V_ARM"), 'group': ['internal_voltages', 'voltages'],
                      'exp_value': _exp_value(1.35,3), 'unit': 'V'},
            'V_DDR': {'method': partial(obj.Mng.get_monitored_board_supplies, "V_DDR"), 'group': ['internal_voltages', 'voltages'],
                      'exp_value': _exp_value(1.35,3), 'unit': 'V'},
            'V_2V5': {'method': partial(obj.Mng.get_monitored_board_supplies, "V_2V5"), 'group': ['internal_voltages', 'voltages'],
                      'exp_value': _exp_value(2.5,5), 'unit': 'V'},
            'V_1V0': {'method': partial(obj.Mng.get_monitored_board_supplies, "V_1V0"), 'group': ['internal_voltages', 'voltages'],
                      'exp_value': _exp_value(1.0,3), 'unit': 'V'},
            'V_1V1': {'method': partial(obj.Mng.get_monitored_board_supplies, "V_1V1"), 'group': ['internal_voltages', 'voltages'],
                      'exp_value': _exp_value(1.1,3), 'unit': 'V'},
            'V_CORE': {'method': partial(obj.Mng.get_monitored_board_supplies, "V_CORE"), 'group': ['internal_voltages', 'voltages'],
                      'exp_value': _exp_value(1.2,3), 'unit': 'V'},
            'V_1V5': {'method': partial(obj.Mng.get_monitored_board_supplies, "V_1V5"), 'group': ['internal_voltages', 'voltages'],
                      'exp_value': _exp_value(1.,3), 'unit': 'V'},
            'V_3V3': {'method': partial(obj.Mng.get_monitored_board_supplies, "V_3V3"), 'group': ['internal_voltages', 'voltages'],
                      'exp_value': _exp_value(3.3,5), 'unit': 'V'},
            'V_5V': {'method': partial(obj.Mng.get_monitored_board_supplies, "V_5V"), 'group': ['internal_voltages', 'voltages'],
                      'exp_value': _exp_value(5.0,5), 'unit': 'V'},
            'V_3V': {'method': partial(obj.Mng.get_monitored_board_supplies, "V_3V"), 'group': ['internal_voltages', 'voltages'],
                      'exp_value': _exp_value(3.0,5), 'unit': 'V'},
            'V_2V8': {'method': partial(obj.Mng.get_monitored_board_supplies, "V_2V8"), 'group': ['internal_voltages', 'voltages'],
                      'exp_value': _exp_value(2.8,5), 'unit': 'V'},
        },
        'smb_powerin_voltage': {
            '12V0': {'method': obj.Mng.get_voltage_smb, 'group': ['smb_powerin_voltage', 'voltages'],
                      'exp_value': _exp_value(12.0,5), 'unit': 'V'},
        },
    }
