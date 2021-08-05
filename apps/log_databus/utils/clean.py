# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making BK-LOG 蓝鲸日志平台 available.
Copyright (C) 2021 THL A29 Limited, a Tencent company.  All rights reserved.
BK-LOG 蓝鲸日志平台 is licensed under the MIT License.
License for BK-LOG 蓝鲸日志平台:
--------------------------------------------------------------------
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial
portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
from collections import namedtuple

from apps.feature_toggle.plugins.constants import SCENARIO_BKDATA
from apps.log_databus.constants import EtlConfig, DEFAULT_ETL_CONFIG
from apps.log_databus.models import CollectorConfig, BKDataClean
from apps.feature_toggle.handlers.toggle import FeatureToggleObject
from apps.utils.log import logger
from apps.utils.bk_data_auth import BkDataAuthHandler


class CleanFilterUtils:
    Cleans = namedtuple(
        "Clean",
        [
            "bk_data_id",
            "collector_config_name",
            "result_table_id",
            "collector_config_id",
            "etl_config",
            "bkdata_auth_url",
            "index_set_id",
            "updated_by",
            "updated_at",
        ],
    )

    def __init__(self, bk_biz_id):
        self.bk_biz_id = bk_biz_id
        self.cleans = []

    def get_collector_config(self):
        collector_configs = (
            CollectorConfig.objects.filter(bk_biz_id=self.bk_biz_id)
            .exclude(index_set_id__isnull=True)
            .exclude(etl_config__isnull=True)
            .exclude(etl_config=EtlConfig.BK_LOG_TEXT)
        )
        for collector_config in collector_configs:
            self.cleans.append(
                self.Cleans(
                    bk_data_id=collector_config.bk_data_id,
                    collector_config_name=collector_config.collector_config_name,
                    result_table_id=collector_config.table_id,
                    collector_config_id=collector_config.collector_config_id,
                    etl_config=collector_config.etl_config,
                    bkdata_auth_url=None,
                    index_set_id=collector_config.index_set_id,
                    updated_by=collector_config.updated_by,
                    updated_at=collector_config.updated_at,
                )
            )

    def get_bkdata_clean(self):
        if not FeatureToggleObject.switch(name=SCENARIO_BKDATA):
            return
        bk_data_cleans = BKDataClean.objects.filter(bk_biz_id=self.bk_biz_id)
        for bk_data_clean in bk_data_cleans:
            collector_config = CollectorConfig.objects.filter(
                collector_config_id=bk_data_clean.collector_config_id
            ).first()
            if not collector_config:
                logger.error("can not find this collector_config {}".format(bk_data_clean.collector_config_id))

            self.cleans.append(
                self.Cleans(
                    bk_data_id=bk_data_clean.raw_data_id,
                    collector_config_name=collector_config.collector_config_name,
                    result_table_id=bk_data_clean.result_table_id,
                    collector_config_id=bk_data_clean.collector_config_id,
                    etl_config=DEFAULT_ETL_CONFIG,
                    bkdata_auth_url=None
                    if bk_data_clean.is_authorized
                    else self.get_auth_url(bk_data_clean.result_table_id),
                    index_set_id=bk_data_clean.log_index_set_id,
                    updated_by=bk_data_clean.updated_by,
                    updated_at=bk_data_clean.updated_at,
                )
            )

    @classmethod
    def get_auth_url(cls, result_table_id):
        return BkDataAuthHandler.get_auth_url([result_table_id])

    @classmethod
    def filter_keyword(cls, clean, keyword):
        if keyword in clean.collector_config_name or keyword in clean.result_table_id:
            return True
        return False

    def filter(self, page, pagesize, keyword="", etl_config=""):
        self.get_collector_config()
        self.get_bkdata_clean()
        page = int(page)
        pagesize = int(pagesize)
        res = []
        for clean in self.cleans:
            if etl_config and clean.etl_config != etl_config:
                continue
            if keyword and not self.filter_keyword(clean=clean, keyword=keyword):
                continue
            res.append(dict(clean._asdict()))

        sorted_res = sorted(res, key=lambda x: x["updated_at"], reverse=True)
        if page and pagesize:
            return {"total": len(sorted_res), "list": sorted_res[(page - 1) * pagesize : page * pagesize]}
        return sorted_res
