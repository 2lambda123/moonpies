# File named "my_config.py"
{
   'run_name': 'custom_run',
   'solar_wind_ice': False,
   'impactor_density': 2000  # [kg m^-3]
}
```

In the above example, the `run_name` parameter is set to "custom_run", the `solar_wind_ice` parameter is set to `False`, and the `impactor_density` parameter is set to 2000 kg/m^3.

## Specifying Parameters in the Configuration File

To specify the desired values for parameters in the configuration file, refer to the `Cfg` class in `moonpies/config.py`. The `Cfg` class provides a full list of parameters and their default values. Make sure the parameter names and value types in the configuration file match those defined in the `Cfg` class.

## Running Moonpies with the Configuration File

Once you have created the custom configuration file, you can run MoonPIES with it using the `-c` or `--cfg` flag. Here's an example command to run MoonPIES with a custom configuration file named "my_config.py":

```bash
moonpies --cfg my_config.py
