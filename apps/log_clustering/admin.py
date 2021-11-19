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
from django.contrib import admin

from apps.log_clustering.models import (
    SampleSet,
    AiopsModel,
    AiopsModelExperiment,
    AiopsSignatureAndPattern,
    ClusteringConfig,
)
from apps.utils.admin import AppModelAdmin


@admin.register(SampleSet)
class SampleSetAdmin(AppModelAdmin):
    list_display = ["sample_set_id", "sample_set_name"]
    search_fields = ["sample_set_id", "sample_set_name"]


@admin.register(AiopsModel)
class AiopsModelAdmin(AppModelAdmin):
    list_display = ["model_id", "model_name"]
    search_fields = ["model_id", "model_name"]


@admin.register(AiopsModelExperiment)
class AiopsModelExperimentAdmin(AppModelAdmin):
    list_display = ["model_id", "experiment_id", "experiment_alias", "status", "basic_model_id", "node_id_list"]
    search_fields = ["model_id", "experiment_id", "experiment_alias", "status", "basic_model_id", "node_id_list"]


@admin.register(AiopsSignatureAndPattern)
class AiopsSignatureAndPatternAdmin(AppModelAdmin):
    list_display = ["model_id", "signature", "pattern"]
    search_fields = ["model_id", "signature", "pattern"]


@admin.register(ClusteringConfig)
class ClusteringConfigAdmin(AppModelAdmin):
    list_display = [
        "collector_config_id",
        "collector_config_name_en",
        "index_set_id",
        "sample_set_id",
        "model_id",
        "min_members",
        "max_dist_list",
        "predefined_varibles",
        "delimeter",
        "max_log_length",
        "is_case_sensitive",
        "clustering_fields",
        "filter_rules",
        "bk_biz_id",
    ]
    search_fields = [
        "collector_id",
        "collector_config_name_en",
        "index_set_id",
        "sample_set_id",
        "model_id",
        "min_members",
        "max_dist_list",
        "predefined_varibles",
        "delimeter",
        "max_log_length",
        "is_case_sensitive",
    ]