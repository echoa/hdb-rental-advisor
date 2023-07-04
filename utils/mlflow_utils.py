"""Utility functions related to setup or usage of mlflow can be defined here"""

import logging
import logging.config
import yaml
import mlflow
import mlflow.sklearn


logger = logging.getLogger(__name__)


def setup_logging(logging_config_path,
                default_level=logging.INFO):
    """Set up configuration for logging utilities.

    Parameters
    ----------
    logging_config_path : str
        Path to YAML file containing configuration for Python logger,
    default_level : logging object, optional, by default logging.INFO
    """
    
    try:
        with open(logging_config_path, "rt") as file:
            log_config = yaml.safe_load(file.read())
        logging.config.dictConfig(log_config)

    except Exception as error:
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=default_level)
        logger.info(error)
        logger.info(
            "Logging config file is not found. Basic config is being used.")

def init(mlflow_uri: str, mlflow_experiment: str,
                setup_mlflow: bool = False, autolog: bool = False):
    """Initialise MLflow connection.

    Parameters
    ----------
    mlflow_uri : str
        the uri of the mlflow tracking server 
        eg "http://[username]:[password]@localhost:5005"
    mlflow_experiment : str
        name of experiment to log under
        eg aiap13-experiment
    setup_mlflow : bool, optional
        Choice to set up MLflow connection, by default False
    autolog : bool, optional
        Choice to set up MLflow's autolog, by default False

    Returns
    -------
    init_success : bool
        Boolean value indicative of success
        of intialising connection with MLflow server.

    mlflow_run : Union[None, `mlflow.entities.Run` object]
        On successful initialisation, the function returns an object
        containing the data and properties for the MLflow run.
        On failure, the function returns a null value.
    """
    init_success = False
    mlflow_run = None
    if setup_mlflow:
        try:
            print(mlflow_uri)
            print(mlflow_experiment)
            mlflow.set_tracking_uri(mlflow_uri)
            mlflow.set_experiment(mlflow_experiment)

            if autolog:
                mlflow.autolog()

            mlflow.start_run()

            mlflow_run = mlflow.active_run()
            init_success = True
            logger.info("MLflow initialisation has succeeded.")
            logger.info("UUID for MLflow run: {}".format(
                mlflow_run.info.run_id))
        except:
            logger.error("MLflow initialisation has failed.")

    return init_success, mlflow_run


def log(mlflow_init_status,
            log_function, **kwargs):
    """Custom function for utilising MLflow's logging functions.

    This function is only relevant when the function `mlflow_init`
    returns a "True" value, translating to a successful initialisation
    of a connection with an MLflow server.

    Parameters
    ----------
    mlflow_init_status : bool
        Boolean value indicative of success of intialising connection
        with MLflow server.
    log_function : str
        Name of MLflow logging function to be used.
        See https://www.mlflow.org/docs/latest/python_api/mlflow.html
    **kwargs
        Keyword arguments passed to `log_function`.
    """
    if mlflow_init_status:
        try:
            method = getattr(mlflow, log_function)
            method(**{key: value for key, value in kwargs.items()
                    if key in method.__code__.co_varnames})
        except Exception as error:
            logger.error(error)


def load_model(path_to_model):
    return mlflow.sklearn.load_model(path_to_model)
