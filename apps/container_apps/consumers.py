import logging
import asyncio
import httpx

from kubernetes_asyncio import client as k8s_aio_client, watch as k8s_aio_watch
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from json import dumps as json_dumps, loads as json_loads
from base64 import b64encode, b64decode
from aiohttp.http import WSMsgType

from aiohttp.client_exceptions import WSServerHandshakeError, ServerDisconnectedError
from autobahn.exception import Disconnected

from .models import ContainerApp

from .resource import AppResource, AppResourceError

from core.settings import env
from ..infra.constants import K8S_WATCH_EVENT_EQS

from core.utils import error_message, get_k8s_api_client, make_hashable
from .utils import process_pod_info, get_stat_from_deployment, process_events, fetch_usage, fetch_metric_server_stat


class BaseAppConsumer(AsyncWebsocketConsumer):
    """
    Base class for consumers that interact with container apps
    """

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.app = None
        self.appid = None
        self.app_resource = None
        self.nsid = None
        self.user_role = None
        self.pod_prefix = None
        self.k8s_client = None
        self.core_v1 = None

    async def authenticate_and_init(self) -> None:
        appid = self.scope['url_route']['kwargs'].get('appid')
        nsid = self.scope['url_route']['kwargs'].get('nsid')
        token = self.scope.get('token')
        user = self.scope['user']

        if not user.is_authenticated:
            raise AppResourceError("Unauthenticated")

        if token:
            if not token.has_app_permission('container-apps', 'WS:R'):
                raise AppResourceError("Token does not have permission to access this resource")
            update_token = database_sync_to_async(lambda: token.update_last_used())
            await update_token()

        if (not nsid) or (not appid):
            raise AppResourceError("nsid and appid are required")

        try:
            self.app = await sync_to_async(ContainerApp.objects.get)(appid=appid, namespace__nsid=nsid)
            get_role = sync_to_async(lambda: self.app.namespace.get_role(user))
            self.user_role = await get_role()

            if self.user_role is None:
                raise AppResourceError("Namespace not found or no permission to access")

            self.nsid = nsid
            self.appid = appid
            self.pod_prefix = f"app-{self.appid}"

        except ContainerApp.DoesNotExist:
            raise AppResourceError("App not found or no permission to access")

    async def init_app_resource(self) -> None:
        create_resource = sync_to_async(lambda: AppResource(self.app))
        self.app_resource = await create_resource()

    async def init_k8s_client(self, ws=False) -> None:
        try:
            self.k8s_client = await get_k8s_api_client(ws=ws)
            self.core_v1 = k8s_aio_client.CoreV1Api(self.k8s_client)
        except Exception as e:
            logging.error(f"Error initializing k8s client: {e}")
            raise AppResourceError("Failed to connect to cluster. Contact support")

    def has_pod_perm(self, pod_name: str) -> bool:
        return pod_name.startswith(self.pod_prefix)

    async def has_container_perm(self, container_name: str) -> bool:
        for c_type in ('main', 'sidecar', 'init'):
            if container_name.startswith(c_type):
                return True
        return False

    async def container_exists(self, pod_name: str, container_name: str) -> bool:
        try:
            pod = await self.core_v1.read_namespaced_pod(name=pod_name, namespace=self.nsid)
            container_names = [container.name for container in pod.spec.containers]

            if container_name in container_names:
                return True

            if pod.spec.init_containers:
                init_container_names = [container.name for container in pod.spec.init_containers]
                if container_name in init_container_names:
                    return True

            return False

        except Exception:
            return False

    async def validate_iref_and_cref(self, iref, cref) -> None:
        if iref is None:
            raise AppResourceError("iref is required")

        if cref is None:
            raise AppResourceError("cref is required")

        if not isinstance(iref, str) or not isinstance(cref, str):
            raise AppResourceError("iref and cref must be strings")

        if not self.has_pod_perm(iref):
            raise AppResourceError("Permission denied: Cannot access this instance")

        if not self.has_container_perm(cref):
            raise AppResourceError("Permission denied: Cannot access this container")

    async def get_pod_names(self, include_terminating=False) -> list[str]:
        pods = await self.core_v1.list_namespaced_pod(namespace=self.nsid, label_selector=f'appid={self.appid}')

        if include_terminating:
            return [pod.metadata.name for pod in pods.items]

        return [pod.metadata.name for pod in pods.items if pod.metadata.deletion_timestamp is None]

    async def disconnect(self, close_code):
        if self.k8s_client:
            await self.k8s_client.close()


class AppConsumer(BaseAppConsumer):
    k8s_config = env.k8s_api_client.configuration
    prometheus_api_url = f"{k8s_config.host}/api/v1/namespaces/prometheus/services/prometheus-server:80/proxy/api/v1"
    metrics_api_url = f"{k8s_config.host}/apis/metrics.k8s.io/v1beta1/namespaces"
    httpx_headers = {'Accept': 'application/json'}
    if token := env.k8s_auth.get('token'):
        httpx_headers['Authorization'] = f"Bearer {token}"
        httpx_kwargs = {'headers': httpx_headers, 'verify': False}
    else:
        httpx_kwargs = {
            'verify': env.k8s_auth['ca_cert'].name,
            'cert': (env.k8s_auth['client_cert'].name, env.k8s_auth['client_key'].name),
            'headers': httpx_headers,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.apps_v1 = None
        self.watch_tasks = {}
        self.pod_in_err = False
        self.pod_dismiss_list = set()

        self.pod_names = set()
        self.limits = {}

    async def connect(self):
        await self.accept()
        try:
            await self.authenticate_and_init()
            await self.init_k8s_client()
            await self.init_app_resource()

            self.apps_v1 = k8s_aio_client.AppsV1Api(self.k8s_client)

        except AppResourceError as e:
            await self.send(text_data=json_dumps(error_message(str(e))))
            await self.close()

    async def watch_pods(self) -> None:
        try:
            params = {
                'namespace': self.nsid,
                'label_selector': f'appid={self.appid}',
            }

            existing_pods = await self.core_v1.list_namespaced_pod(**params, timeout_seconds=5)

            params['resource_version'] = existing_pods.metadata.resource_version

            sorted_pods = sorted(existing_pods.items, key=lambda x: x.metadata.creation_timestamp)

            for pod in sorted_pods:
                pod_info = process_pod_info(pod)
                self.pod_names.add(pod_info['iref'])
                await self.send(text_data=json_dumps({
                    'instance': {
                        'event': 'add',
                        'data': pod_info
                    }
                }))
                await asyncio.sleep(0.05)

            async with k8s_aio_watch.Watch().stream(self.core_v1.list_namespaced_pod, **params) as stream:
                async for event in stream:
                    evt, obj = event["type"], event["object"]
                    pod_info = process_pod_info(obj)

                    # Sometimes, watch returns an immature object without all info, when a pod is first created.
                    # In that case, we skip sending it till all data becomes available in a modify event later.

                    override_evt = False
                    if (evt == 'ADDED' or evt == 'MODIFIED') and pod_info['state'] is None:
                        self.pod_dismiss_list.add(pod_info['iref'])
                        continue

                    if pod_info['iref'] in self.pod_dismiss_list:
                        self.pod_dismiss_list.remove(pod_info['iref'])
                        override_evt = True

                    # For keeping track of pods for usage stats
                    if evt == 'DELETED':
                        self.pod_names.remove(pod_info['iref'])
                    else:
                        self.pod_names.add(pod_info['iref'])

                    await self.send(text_data=json_dumps({
                        'instance': {
                            'event': K8S_WATCH_EVENT_EQS[evt] if not override_evt else 'add',
                            'data': pod_info
                        }
                    }))

        except asyncio.CancelledError:
            pass

        except Exception:
            raise AppResourceError(f"Error watching instances")

    async def watch_deployment(self) -> None:
        try:
            params = {
                'namespace': self.nsid,
                'label_selector': f'appid={self.appid}',
            }

            async with k8s_aio_watch.Watch().stream(self.apps_v1.list_namespaced_deployment, **params) as stream:
                async for event in stream:
                    evt, obj = event["type"], event["object"]

                    if evt == 'DELETED':
                        await self.send(text_data=json_dumps(error_message("App has been deleted")))
                        await self.close()
                    else:
                        stat = get_stat_from_deployment(obj)
                        await self.send(text_data=json_dumps({'stat': stat}))

        except asyncio.CancelledError:
            pass

        except Exception:
            raise AppResourceError(f"Error watching stat")

    async def watch_events(self) -> None:
        try:
            params = {
                'namespace': self.nsid,
                'field_selector': f'involvedObject.name=app-{self.appid}',
                'timeout_seconds': 5
            }

            event_hash = None

            while True:
                events = await self.core_v1.list_namespaced_event(**params)
                event_messages = process_events(events)
                current_hash = hash(make_hashable(event_messages))

                if event_hash != current_hash:
                    await self.send(text_data=json_dumps({'events': event_messages}))

                event_hash = current_hash

                await asyncio.sleep(10)

        except asyncio.CancelledError:
            pass

        except k8s_aio_client.exceptions.ApiException as e:
            if e.status == 404 or e.status == 400:
                raise AppResourceError("App has been deleted")
            else:
                raise AppResourceError(f"Failed to get events")

        except Exception:
            raise AppResourceError(f"Error watching events")

    async def watch_usage(self) -> None:
        sel = f'service=~"{self.nsid}-route-{self.appid}.*"'

        p_queries = {
            'response_bytes': f'sum(traefik_service_responses_bytes_total{{{sel}}})',
            'request_bytes': f'sum(traefik_service_requests_bytes_total{{{sel}}})',
            'request_count': f'sum(traefik_service_requests_total{{{sel}}})',
        }

        event_hash = None

        async with httpx.AsyncClient(**self.httpx_kwargs) as client:
            while True:
                try:
                    p_tasks = [
                        fetch_usage(client, f"{self.prometheus_api_url}/query", query, name)
                        for name, query in p_queries.items()
                    ]

                    if self.pod_names:
                        pods = list(self.pod_names)
                    else:
                        pods = await self.get_pod_names()

                    m_tasks = [
                        fetch_metric_server_stat(client, f"{self.metrics_api_url}/{self.nsid}/pods/{pod_name}")
                        for pod_name in pods
                    ]

                    p_results = dict(zip(p_queries.keys(), await asyncio.gather(*p_tasks)))
                    m_results = dict(zip(pods, await asyncio.gather(*m_tasks)))

                    cpu_total = 0
                    mem_total = 0

                    for pod in m_results.values():
                        cpu_total += pod['total']['cpu']
                        mem_total += pod['total']['memory']

                    cpu_total = round(cpu_total, 2)
                    mem_total = round(mem_total, 2)

                    result = {
                        'usage': {
                            **p_results,
                            'cpu': cpu_total,
                            'memory': mem_total,
                        },
                    }

                    current_hash = hash(make_hashable(result))

                    if event_hash != current_hash:
                        await self.send(text_data=json_dumps(result))

                    event_hash = current_hash

                    await asyncio.sleep(5)

                except asyncio.CancelledError:
                    break

                except Exception:
                    raise AppResourceError(f"Error fetching usage")

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json_loads(text_data)
            watch_type = data.get('watch')

            if task := self.watch_tasks.get(watch_type):
                task.cancel()

            if watch_type == 'instances':
                self.watch_tasks[watch_type] = asyncio.create_task(self.watch_pods())

            elif watch_type == 'stat':
                self.watch_tasks[watch_type] = asyncio.create_task(self.watch_deployment())

            elif watch_type == 'events':
                self.watch_tasks[watch_type] = asyncio.create_task(self.watch_events())

            elif watch_type == 'usage':
                self.watch_tasks[watch_type] = asyncio.create_task(self.watch_usage())

        except asyncio.CancelledError:
            pass

        except AppResourceError as e:
            await self.send(text_data=json_dumps(error_message(str(e))))
            await self.close()

        except Exception as e:
            logging.error("Error in receive: %s", e)
            await self.send(text_data=json_dumps(error_message("Internal server error")))
            await self.close()

    async def disconnect(self, close_code):
        for task in self.watch_tasks.values():
            task.cancel()

        await super().disconnect(close_code)


STDOUT_CHANNEL = 1
STDERR_CHANNEL = 2
ERROR_CHANNEL = 3
EXEC_CMD = [
    '/bin/sh',
    '-c',
    'TERM=xterm-256color; export TERM; [ -x /bin/bash ] && ([ -x /usr/bin/script ] && /usr/bin/script -q -c '
    '"/bin/bash" /dev/null || exec /bin/bash) || exec /bin/sh'
]


class TerminalConsumer(BaseAppConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ws_connection = None
        self.read_task = None
        self.exec_coroutine = None

    async def connect(self):
        await self.accept()

        iref = self.scope['url_route']['kwargs'].get('iref')
        cref = self.scope['url_route']['kwargs'].get('cref')

        try:
            await self.authenticate_and_init()
            await self.init_k8s_client(ws=True)
            await self.validate_iref_and_cref(iref, cref)
            await self.start_shell(iref, cref)

        except AppResourceError as e:
            await self.send(text_data=f"msg:{str(e)}")
            await self.close()

        except Exception as e:
            logging.error(f"Error in connect: {e}")
            await self.send(text_data=f"msg:Internal server error")
            await self.close()

    async def start_shell(self, iref, cref):
        try:
            self.exec_coroutine = self.core_v1.connect_get_namespaced_pod_exec(name=iref,
                                                                               namespace=self.nsid,
                                                                               container=cref,
                                                                               command=EXEC_CMD,
                                                                               stderr=True,
                                                                               stdin=True,
                                                                               stdout=True,
                                                                               tty=True,
                                                                               _preload_content=False
                                                                               )

            self.read_task = asyncio.create_task(self.read_from_shell())

        except k8s_aio_client.exceptions.ApiException as e:
            if e.status == 404:
                raise AppResourceError("Container does not support shell or is not running")
            elif e.status == 400:
                raise AppResourceError(f"Failed to initialize shell")
        except Exception as e:
            logging.error(f"Error while creating shell connection: {e}")
            raise AppResourceError("Internal server error")

    async def read_from_shell(self):
        try:
            async with await self.exec_coroutine as ws:
                self.ws_connection = ws
                while True:
                    try:
                        msg = await ws.receive(timeout=0.1)
                    except asyncio.TimeoutError:
                        continue

                    if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
                        await self.send(text_data=f"msg:Closing shell")
                        await self.close()
                        break

                    if msg.type != WSMsgType.BINARY:
                        continue

                    if not msg.data or len(msg.data) < 2:
                        continue

                    channel = msg.data[0]
                    data = msg.data[1:].decode("utf-8", errors="replace")

                    if not data:
                        continue

                    if channel == STDOUT_CHANNEL:
                        try:
                            encoded_data = b64encode(data.encode('utf-8', errors='replace')).decode('utf-8')
                            await self.send(text_data=f"stdout:{encoded_data}")
                        except Exception as e:
                            logging.error(f"Error encoding stdout: {e}")
                            await self.send(text_data=data)

                    elif channel == STDERR_CHANNEL:
                        try:
                            encoded_error = b64encode(data.encode('utf-8', errors='replace')).decode('utf-8')
                            await self.send(text_data=f"stderr:{encoded_error}")
                        except Exception as e:
                            logging.error(f"Error encoding stderr: {e}")
                            await self.send(text_data=data)

                    elif channel == ERROR_CHANNEL:
                        try:
                            error_data = json_loads(data)
                            if error_data.get('status') == 'Failure':
                                await self.send(text_data=f"msg:Container does not support shell or is not running")
                                await self.close()
                            else:
                                logging.error(f"Error from exec: {error_data}")
                        except Exception as e:
                            logging.error(f"Error from exec: {e}")

                    await asyncio.sleep(0.01)  # To prevent CPU hogging

        except (asyncio.CancelledError, ServerDisconnectedError, Disconnected):
            pass

        except WSServerHandshakeError:
            await self.send(text_data=f"msg:Container does not support shell or is not running")
            await self.close()

        except Exception as e:
            logging.error(f"Error in read_from_shell: {e}")
            await self.send(text_data=f"msg:Internal server error")
            await self.close()

    async def receive(self, text_data=None, bytes_data=None):
        """
        Directly pass input to the container
        """
        if not self.ws_connection or not text_data:
            return None

        try:
            # Handle terminal resize
            if text_data.startswith('resize:'):
                try:
                    parts = text_data.split(':')  # Format: resize:cols:rows
                    if len(parts) == 3:
                        cols = int(parts[1])
                        rows = int(parts[2])
                        await self.set_terminal_size(cols, rows)
                except (ValueError, IndexError):
                    await self.send(text_data=f"msg:Invalid terminal resize message")
            else:
                try:
                    decoded_text = b64decode(text_data).decode('utf-8')
                    await self.send_stdin(decoded_text)
                except Exception:
                    await self.send(text_data=f"msg:Error decoding input")

        except Exception:
            await self.send(text_data=f"msg:Error sending command")
            await self.close()

    async def send_stdin(self, data):
        """
        Send data to stdin channel of the exec websocket
        """
        if not self.ws_connection:
            logging.warning("WebSocket connection not initialized yet")
            return

        try:
            stdin_channel_prefix = chr(0)
            await self.ws_connection.send_bytes((stdin_channel_prefix + data).encode("utf-8"))
        except Exception as e:
            logging.error(f"Error sending stdin data: {e}")
            await self.send(text_data=f"msg:Error sending command")
            await self.close()

    async def set_terminal_size(self, cols, rows):
        for _ in range(10):
            if not self.ws_connection or not self.core_v1:
                await asyncio.sleep(0.5)
            else:
                break

        try:
            resize_message = json_dumps({"Width": cols, "Height": rows})
            control_channel_prefix = chr(4)
            await self.ws_connection.send_bytes((control_channel_prefix + resize_message).encode("utf-8"))
        except Exception:
            await self.send_stdin(f"msg:stty error. Terminal may not work as expected")

    async def disconnect(self, close_code):
        if self.read_task and not self.read_task.done():
            self.read_task.cancel()
            try:
                await self.read_task
            except asyncio.CancelledError:
                pass

        if self.ws_connection:
            await self.ws_connection.close()

        await super().disconnect(close_code)


class LogsConsumer(BaseAppConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iref = None
        self.cref = None
        self.tail_lines = 100
        self.stream = None
        self.closing = False
        self.log_task = None
        self.check_task = None

    async def connect(self):
        await self.accept()

        self.iref = self.scope['url_route']['kwargs'].get('iref')
        self.cref = self.scope['url_route']['kwargs'].get('cref')

        try:
            await self.authenticate_and_init()
            await self.validate_iref_and_cref(self.iref, self.cref)
            await self.init_k8s_client()

            self.log_task = asyncio.create_task(self.stream_logs())
            self.check_task = asyncio.create_task(self.container_check())

        except AppResourceError as e:
            await self.send(text_data=json_dumps(error_message(str(e))))
            await self.close()

        except Exception as e:
            logging.error(f"Error in connect: {e}")
            await self.send(text_data=json_dumps(error_message("Internal server error")))
            await self.disconnect(1)

    async def container_check(self):
        try:
            while not self.closing:
                if not await self.container_exists(self.iref, self.cref):
                    self.closing = True
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass

    async def stream_logs(self):
        try:
            self.stream = await self.core_v1.read_namespaced_pod_log(
                name=self.iref,
                namespace=self.nsid,
                container=self.cref,
                follow=True,
                tail_lines=self.tail_lines,
                timestamps=True,
                pretty=True,
                _preload_content=False
            )

            while not self.closing:
                try:
                    line = await asyncio.wait_for(self.stream.content.readline(), timeout=5.0)
                    if not line:
                        continue

                    line_str = line.decode('utf-8').strip()
                    await self.send(text_data=json_dumps({'log': line_str}))

                except asyncio.TimeoutError:
                    continue

                finally:
                    await asyncio.sleep(0.01)

            else:
                await self.send(text_data=json_dumps(error_message("Container has been terminated")))
                await self.close()

        except asyncio.CancelledError:
            pass

        except k8s_aio_client.exceptions.ApiException as e:
            if e.status == 404 or e.status == 400:
                raise AppResourceError("Container does not exist or has been terminated")
            else:
                raise AppResourceError("Failed to stream logs")

        except Exception as e:
            logging.error("Error in stream_logs", e)
            raise AppResourceError("Internal server error")

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json_loads(text_data)
            tail_lines = data.get('tail_lines')

            if not isinstance(tail_lines, int):
                await self.send(text_data=json_dumps(error_message('Invalid tail_lines parameter')))
                return None

            if tail_lines < 0:
                await self.send(text_data=json_dumps(error_message('tail_lines must be a positive integer')))
                return None

            if self.tail_lines == tail_lines:
                return None

            self.tail_lines = tail_lines

            await self.stop_streaming()
            await asyncio.sleep(0.01)

            self.closing = False

            self.log_task = asyncio.create_task(self.stream_logs())
            self.check_task = asyncio.create_task(self.container_check())

        except Exception as e:
            logging.error(f"Error in log receive", e)
            raise AppResourceError("Bad request")

    async def stop_streaming(self):
        self.closing = True

        if self.check_task and not self.check_task.done():
            self.check_task.cancel()
            try:
                await self.check_task
            except asyncio.CancelledError:
                pass

        # Fix: Check if self.stream is not None and close it without awaiting
        if self.stream:
            try:
                self.stream.close()  # Remove the await here
            except Exception as e:
                logging.error(f"Error closing stream: {e}")
            finally:
                self.stream = None

        if self.log_task and not self.log_task.done():
            self.log_task.cancel()
            try:
                await self.log_task
            except asyncio.CancelledError:
                pass

    async def disconnect(self, close_code):
        await self.stop_streaming()
        await super().disconnect(close_code)
