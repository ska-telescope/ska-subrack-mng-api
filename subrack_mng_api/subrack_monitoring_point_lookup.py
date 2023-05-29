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


def load_subrack_lookup(obj):
    return{
        'temperatures': {
            'SMM1'   : {'method': partial(obj.Mng.GetMngTemp, sens_id = 1),      "exp_value": { "min": 10.00, "max": 68.00}, 'unit' : 'C'},
            'SMM2'   : {'method': partial(obj.Mng.GetMngTemp, sens_id = 2),      "exp_value": { "min": 10.00, "max": 68.00}, 'unit' : 'C'},
            'BKPLN1' : {'method': partial(obj.Bkpln.get_sens_temp, sens_id = 1), "exp_value": { "min": 10.00, "max": 68.00}, 'unit' : 'C'},
            'BKPLN2' : {'method': partial(obj.Bkpln.get_sens_temp, sens_id = 2), "exp_value": { "min": 10.00, "max": 68.00}, 'unit' : 'C'},
        },
        'fans' : {
            'speed' : {
                'FAN1'   : {'method': partial(obj.GetFanRpm, fan_id = 1), "exp_value": { "min": None, "max": None}, 'unit' : 'rpm'},
                'FAN2'   : {'method': partial(obj.GetFanRpm, fan_id = 2), "exp_value": { "min": None, "max": None}, 'unit' : 'rpm'},
                'FAN3'   : {'method': partial(obj.GetFanRpm, fan_id = 3), "exp_value": { "min": None, "max": None}, 'unit' : 'rpm'},
                'FAN4'   : {'method': partial(obj.GetFanRpm, fan_id = 4), "exp_value": { "min": None, "max": None}, 'unit' : 'rpm'},
            },
            'pwm_duty' : {
                'FAN1'   : {'method': partial(obj.GetFanPwm, fan_id = 1), "exp_value": { "min": None, "max": None}, 'unit' : '%'},
                'FAN2'   : {'method': partial(obj.GetFanPwm, fan_id = 2), "exp_value": { "min": None, "max": None}, 'unit' : '%'},
                'FAN3'   : {'method': partial(obj.GetFanPwm, fan_id = 3), "exp_value": { "min": None, "max": None}, 'unit' : '%'},
                'FAN4'   : {'method': partial(obj.GetFanPwm, fan_id = 4), "exp_value": { "min": None, "max": None}, 'unit' : '%'},
            },
            'mode' : {
                'FAN1'   : {'method': partial(obj.GetFanMode, fan_id = 1), "exp_value": { "min": None, "max": None}, 'unit' : ''},
                'FAN2'   : {'method': partial(obj.GetFanMode, fan_id = 2), "exp_value": { "min": None, "max": None}, 'unit' : ''},
                'FAN3'   : {'method': partial(obj.GetFanMode, fan_id = 3), "exp_value": { "min": None, "max": None}, 'unit' : ''},
                'FAN4'   : {'method': partial(obj.GetFanMode, fan_id = 4), "exp_value": { "min": None, "max": None}, 'unit' : ''},
            },
            
        },
        'psus': {
            'status' : {
                'PSU1'   : {'method': partial(obj.Bkpln.get_ps_status, ps_id = 1), "exp_value": { "min": None, "max": None}, 'unit' : 'V'},
                'PSU2'   : {'method': partial(obj.Bkpln.get_ps_status, ps_id = 2), "exp_value": { "min": None, "max": None}, 'unit' : 'V'},
            },
            'voltage' : {
                'PSU1'   : {'method': partial(obj.GetPSVout, ps_id = 1), "exp_value": { "min": None, "max": None}, 'unit' : 'V'},
                'PSU2'   : {'method': partial(obj.GetPSVout, ps_id = 2), "exp_value": { "min": None, "max": None}, 'unit' : 'V'},
            },
            'current' : {
                'PSU1'   : {'method': partial(obj.GetPSIout, ps_id = 1), "exp_value": { "min": None, "max": None}, 'unit' : 'A'},
                'PSU2'   : {'method': partial(obj.GetPSIout, ps_id = 2), "exp_value": { "min": None, "max": None}, 'unit' : 'A'},
            },
            'fan_pwm_or' : {
                'PSU1'   : {'method': partial(obj.GetPSFanSpeed, ps_id = 1), "exp_value": { "min": None, "max": None}, 'unit' : 'rpm'},
                'PSU2'   : {'method': partial(obj.GetPSFanSpeed, ps_id = 2), "exp_value": { "min": None, "max": None}, 'unit' : 'rpm'},
            },
        },
        'slots': {
            'presence' : {
                'SLOT1'   : {'method': partial(obj.GetTPMPresent, tpm_slot_id = 1), "exp_value": { "min": None, "max": None}, 'unit' : ''},
                'SLOT2'   : {'method': partial(obj.GetTPMPresent, tpm_slot_id = 2), "exp_value": { "min": None, "max": None}, 'unit' : ''},
                'SLOT3'   : {'method': partial(obj.GetTPMPresent, tpm_slot_id = 3), "exp_value": { "min": None, "max": None}, 'unit' : ''},
                'SLOT4'   : {'method': partial(obj.GetTPMPresent, tpm_slot_id = 4), "exp_value": { "min": None, "max": None}, 'unit' : ''},
                'SLOT5'   : {'method': partial(obj.GetTPMPresent, tpm_slot_id = 5), "exp_value": { "min": None, "max": None}, 'unit' : ''},
                'SLOT6'   : {'method': partial(obj.GetTPMPresent, tpm_slot_id = 6), "exp_value": { "min": None, "max": None}, 'unit' : ''},
                'SLOT7'   : {'method': partial(obj.GetTPMPresent, tpm_slot_id = 7), "exp_value": { "min": None, "max": None}, 'unit' : ''},
                'SLOT8'   : {'method': partial(obj.GetTPMPresent, tpm_slot_id = 8), "exp_value": { "min": None, "max": None}, 'unit' : ''},
            },
            'on' : {
                'SLOT1'   : {'method': partial(obj.Bkpln.is_tpm_on, tpm_id = 1), "exp_value": { "min": None, "max": None}, 'unit' : ''},
                'SLOT2'   : {'method': partial(obj.Bkpln.is_tpm_on, tpm_id = 2), "exp_value": { "min": None, "max": None}, 'unit' : ''},
                'SLOT3'   : {'method': partial(obj.Bkpln.is_tpm_on, tpm_id = 3), "exp_value": { "min": None, "max": None}, 'unit' : ''},
                'SLOT4'   : {'method': partial(obj.Bkpln.is_tpm_on, tpm_id = 4), "exp_value": { "min": None, "max": None}, 'unit' : ''},
                'SLOT5'   : {'method': partial(obj.Bkpln.is_tpm_on, tpm_id = 5), "exp_value": { "min": None, "max": None}, 'unit' : ''},
                'SLOT6'   : {'method': partial(obj.Bkpln.is_tpm_on, tpm_id = 6), "exp_value": { "min": None, "max": None}, 'unit' : ''},
                'SLOT7'   : {'method': partial(obj.Bkpln.is_tpm_on, tpm_id = 7), "exp_value": { "min": None, "max": None}, 'unit' : ''},
                'SLOT8'   : {'method': partial(obj.Bkpln.is_tpm_on, tpm_id = 8), "exp_value": { "min": None, "max": None}, 'unit' : ''},
            },
            'voltage' : {
                'SLOT1'   : {'method': partial(obj.Bkpln.get_voltage_tpm, tpm_id = 1), "exp_value": { "min": 0.00, "max": 12.60}, 'unit' : 'V'},
                'SLOT2'   : {'method': partial(obj.Bkpln.get_voltage_tpm, tpm_id = 2), "exp_value": { "min": 0.00, "max": 12.60}, 'unit' : 'V'},
                'SLOT3'   : {'method': partial(obj.Bkpln.get_voltage_tpm, tpm_id = 3), "exp_value": { "min": 0.00, "max": 12.60}, 'unit' : 'V'},
                'SLOT4'   : {'method': partial(obj.Bkpln.get_voltage_tpm, tpm_id = 4), "exp_value": { "min": 0.00, "max": 12.60}, 'unit' : 'V'},
                'SLOT5'   : {'method': partial(obj.Bkpln.get_voltage_tpm, tpm_id = 5), "exp_value": { "min": 0.00, "max": 12.60}, 'unit' : 'V'},
                'SLOT6'   : {'method': partial(obj.Bkpln.get_voltage_tpm, tpm_id = 6), "exp_value": { "min": 0.00, "max": 12.60}, 'unit' : 'V'},
                'SLOT7'   : {'method': partial(obj.Bkpln.get_voltage_tpm, tpm_id = 7), "exp_value": { "min": 0.00, "max": 12.60}, 'unit' : 'V'},
                'SLOT8'   : {'method': partial(obj.Bkpln.get_voltage_tpm, tpm_id = 8), "exp_value": { "min": 0.00, "max": 12.60}, 'unit' : 'V'},
            },
            'power' : {
                'SLOT1'   : {'method': partial(obj.Bkpln.get_power_tpm, tpm_id = 1), "exp_value": { "min": 0.00, "max": 12.60}, 'unit' : 'W'},
                'SLOT2'   : {'method': partial(obj.Bkpln.get_power_tpm, tpm_id = 2), "exp_value": { "min": 0.00, "max": 12.60}, 'unit' : 'W'},
                'SLOT3'   : {'method': partial(obj.Bkpln.get_power_tpm, tpm_id = 3), "exp_value": { "min": 0.00, "max": 12.60}, 'unit' : 'W'},
                'SLOT4'   : {'method': partial(obj.Bkpln.get_power_tpm, tpm_id = 4), "exp_value": { "min": 0.00, "max": 12.60}, 'unit' : 'W'},
                'SLOT5'   : {'method': partial(obj.Bkpln.get_power_tpm, tpm_id = 5), "exp_value": { "min": 0.00, "max": 12.60}, 'unit' : 'W'},
                'SLOT6'   : {'method': partial(obj.Bkpln.get_power_tpm, tpm_id = 6), "exp_value": { "min": 0.00, "max": 12.60}, 'unit' : 'W'},
                'SLOT7'   : {'method': partial(obj.Bkpln.get_power_tpm, tpm_id = 7), "exp_value": { "min": 0.00, "max": 12.60}, 'unit' : 'W'},
                'SLOT8'   : {'method': partial(obj.Bkpln.get_power_tpm, tpm_id = 8), "exp_value": { "min": 0.00, "max": 12.60}, 'unit' : 'W'},
            }

        }

    }