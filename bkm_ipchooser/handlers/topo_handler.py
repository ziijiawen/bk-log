# -*- coding: utf-8 -*-
import logging
import typing

from bkm_ipchooser import constants, types
from bkm_ipchooser.api import BkApi
from bkm_ipchooser.tools import topo_tool
from bkm_ipchooser.handlers.base import BaseHandler

logger = logging.getLogger("bkm_ipchooser")


class TopoHandler:
    @staticmethod
    def format2tree_node(node: types.ReadableTreeNode) -> types.TreeNode:
        return {
            "bk_obj_id": node["object_id"],
            "bk_inst_id": node["instance_id"],
            "bk_biz_id": node["meta"]["bk_biz_id"],
        }

    @staticmethod
    def format_tree(topo_tree: types.TreeNode) -> types.ReadableTreeNode:
        bk_biz_id: int = topo_tree["bk_inst_id"]
        topo_tree_stack: typing.List[types.TreeNode] = [topo_tree]
        # 定义一个通过校验的配置根节点及栈结构，同步 topo_tree_stack 进行遍历写入
        formatted_topo_tree: types.ReadableTreeNode = {}
        formatted_topo_tree_stack: typing.List[types.ReadableTreeNode] = [formatted_topo_tree]

        # 空间换时间，迭代模拟递归
        while topo_tree_stack:
            # 校验节点
            node = topo_tree_stack.pop()
            # 与 topo_tree_stack 保持相同的遍历顺序，保证构建拓扑树与给定的一致
            formatted_node = formatted_topo_tree_stack.pop()
            formatted_node.update(
                {
                    "instance_id": node["bk_inst_id"],
                    "instance_name": node["bk_inst_name"],
                    "object_id": node["bk_obj_id"],
                    "object_name": node["bk_obj_name"],
                    "meta": BaseHandler.get_meta_data(bk_biz_id),
                    "count": node.get("count", 0),
                    "child": [],
                    "expanded": True,
                }
            )
            child_nodes = node.get("child", [])
            topo_tree_stack.extend(child_nodes)
            formatted_node["child"] = [{} for __ in range(len(child_nodes))]
            formatted_topo_tree_stack.extend(formatted_node["child"])

        return formatted_topo_tree

    @classmethod
    def trees(cls, scope_list: types.ScopeList) -> typing.List[typing.Dict]:
        if len(scope_list) == 0:
            return []

        return [cls.format_tree(topo_tool.TopoTool.get_topo_tree_with_count(scope_list[0]["bk_biz_id"]))]

    @classmethod
    def query_hosts(
        cls,
        readable_node_list: typing.List[types.ReadableTreeNode],
        conditions: typing.List[types.Condition],
        start: int,
        page_size: int,
        fields: typing.List[str] = constants.CommonEnum.DEFAULT_HOST_FIELDS.value,
    ) -> typing.Dict:
        """
        查询主机
        :param readable_node_list: 拓扑节点
        :param conditions: 查询条件，TODO: 暂不支持
        :param fields: 字段
        :param start: 数据起始位置
        :param page_size: 拉取数据数量
        :return:
        """
        if not readable_node_list:
            # 不存在查询节点提前返回，减少非必要 IO
            return {"total": 0, "data": []}

        tree_node: types.TreeNode = cls.format2tree_node(readable_node_list[0])

        # 获取主机信息
        resp = cls.query_cc_hosts(readable_node_list, conditions, start, page_size, fields, return_status=True)

        return {"total": resp["count"], "data": BaseHandler.format_hosts(resp["info"], tree_node["bk_biz_id"])}

    @classmethod
    def query_host_id_infos(
        cls,
        readable_node_list: typing.List[types.ReadableTreeNode],
        conditions: typing.List[types.Condition],
        start: int,
        page_size: int,
    ) -> typing.Dict:
        """
        查询主机 ID 信息
        :param readable_node_list: 拓扑节点
        :param conditions: 查询条件
        :param start: 数据起始位置
        :param page_size: 拉取数据数量
        :return:
        """
        if not readable_node_list:
            # 不存在查询节点提前返回，减少非必要 IO
            return {"total": 0, "data": []}

        tree_node: types.TreeNode = cls.format2tree_node(readable_node_list[0])

        # TODO: 支持全量查询
        page_size = page_size if page_size > 0 else 1000

        # 获取主机信息
        resp = cls.query_cc_hosts(
            readable_node_list,
            conditions,
            start,
            page_size,
            ["bk_host_id", "bk_host_innerip", "bk_host_innerip_v6", "bk_cloud_id"],
        )

        return {"total": resp["count"], "data": BaseHandler.format_host_id_infos(resp["info"], tree_node["bk_biz_id"])}

    @classmethod
    def fill_agent_status(cls, cc_hosts):

        if not cc_hosts:
            return

        index = 0
        hosts, host_map = [], {}
        for cc_host in cc_hosts:
            ip, bk_cloud_id = cc_host["bk_host_innerip"], cc_host["bk_cloud_id"]
            hosts.append({"ip": ip, "bk_cloud_id": bk_cloud_id})

            host_map[f"{bk_cloud_id}:{ip}"] = index
            index += 1

        try:
            status_map = BkApi.get_agent_status({"hosts": hosts})

            for ip_cloud, detail in status_map.items():
                cc_hosts[host_map[ip_cloud]]["status"] = detail["bk_agent_alive"]
        except KeyError as e:
            logger.exception("fill_agent_status exception: %s", e)

    @classmethod
    def fill_cloud_name(cls, cc_hosts):
        if not cc_hosts:
            return

        # 补充云区域名称
        resp = BkApi.search_cloud_area({"page": {"start": 0, "limit": 1000}})

        cloud_map = (
            {cloud_info["bk_cloud_id"]: cloud_info["bk_cloud_name"] for cloud_info in resp["info"]}
            if resp.get("info")
            else {}
        )

        for host in cc_hosts:
            host["bk_cloud_name"] = cloud_map.get(host["bk_cloud_id"], host["bk_cloud_id"])

    @classmethod
    def search_cc_hosts(cls, bk_biz_id, role_host_ids, keyword):
        """搜索主机"""

        if not role_host_ids:
            return []

        # 生成主机过滤条件
        rules = [{"field": "bk_host_id", "operator": "in", "value": role_host_ids}]
        limit = len(role_host_ids)

        if keyword:
            rules.append(
                {
                    "condition": "OR",
                    "rules": [
                        {"field": field, "operator": "contains", "value": key}
                        for key in keyword.split()
                        for field in ["bk_host_name", "bk_host_innerip"]
                    ],
                }
            )

        # 获取主机信息
        resp = BkApi.list_biz_hosts(
            {
                "bk_biz_id": bk_biz_id,
                "fields": [
                    "bk_host_id",
                    "bk_host_innerip",
                    "bk_host_innerip_v6",
                    "bk_cloud_id",
                    "bk_host_name",
                    "bk_os_name",
                    "bk_os_type",
                    "bk_agent_id",
                    "bk_cloud_vendor",
                    "bk_mem",
                    "bk_cpu",
                    "bk_machine_type",
                ],
                "page": {"start": 0, "limit": limit, "sort": "bk_host_innerip"},
                "host_property_filter": {"condition": "AND", "rules": rules},
            },
        )
        hosts = resp["info"]

        # TODO: 抽取常用cc查询接口到一个单独的文件，目前components下很多文件都没用，比如：components/cc,cmdb,itsm等
        TopoHandler.fill_agent_status(hosts)
        TopoHandler.fill_cloud_name(hosts)

        return hosts

    @classmethod
    def query_cc_hosts(
        cls,
        readable_node_list: typing.List[types.ReadableTreeNode],
        conditions: typing.List[types.Condition],
        start: int,
        page_size: int,
        fields: typing.List[str] = constants.CommonEnum.DEFAULT_HOST_FIELDS.value,
        return_status: bool = False,
    ) -> typing.Dict:
        """
        查询主机
        :param readable_node_list: 拓扑节点
        :param conditions: 查询条件
        :param fields: 字段
        :param start: 数据起始位置
        :param page_size: 拉取数据数量
        :param return_status: 返回agent状态
        :return:
        """

        # 查询主机
        tree_node: types.TreeNode = cls.format2tree_node(readable_node_list[0])

        instance_id = tree_node["bk_inst_id"]
        object_id = tree_node["bk_obj_id"]

        params = {
            "bk_biz_id": tree_node["bk_biz_id"],
            "fields": fields,
            "page": {"start": start, "limit": page_size, "sort": "bk_host_innerip"},
        }

        # rules不能为空
        if conditions:
            params.update({"host_property_filter": {"condition": "OR", "rules": conditions}})

        if object_id == "module":
            params.update(bk_module_ids=[instance_id])

        if object_id == "set":
            params.update(bk_set_ids=[instance_id])

        # 获取主机信息
        resp = BkApi.list_biz_hosts(params)

        if resp["info"] and return_status:
            cls.fill_agent_status(resp["info"])

        return resp