<template>
  <div>session id: {{ sessionId }}</div>
  <div class="container">
    <Stepper value="1">
      <StepItem value="1">
        <Step>Input, Platform</Step>
        <StepPanel v-slot="{ activateCallback }">
          <Card style="width: 60rem; overflow: hidden">
            <template #title>Input, Platform</template>
            <template #subtitle
              >Fill in the Gitlab issue number to automatically download the sample file, detect platform and
              notes.</template
            >
            <template #content>
              <div class="flex items-center gap-2">
                <span>Gitlab Issue ID (without #): </span>
                <InputNumber v-model="userInfo.gitlab_issue" style="width: 200px" :useGrouping="false" />
                <Button label="Fill from issue" @click="() => fillFromGitlab()" severity="info" />
              </div>
              {{ fetchingIssueStatus }}
              <div v-if="stepNumber >= 2">
                <Card class="!bg-white rounded-xl border border-slate-200 p-2 mt-5">
                  <template #content>
                    <div class="font-bold text-lg">Input Information</div>
                    <div>This section puts together information from customer, Gitlab issue and provided file.</div>
                    <div class="mt-2">
                      <span class="font-bold"
                        >Note (any infofrom the customer, want to take into account for processing):</span
                      >
                      <Textarea v-model="userInfo.user_comment" rows="4" cols="65" />
                    </div>
                    <div>
                      <span class="font-bold">GItlab Issue:</span>
                      <a
                        :href="gitlabIssueUrl"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="text-blue-600 hover:underline"
                      >
                        #{{ userInfo.gitlab_issue }}
                      </a>
                    </div>
                    <div>
                      <span class="font-bold">Downloaded File:</span> {{ selectedFileName }}
                      <span v-if="selectedFileName" class="text-green-600 ml-1">✓</span>
                      <span v-else>-</span>
                    </div>
                    <div><span class="font-bold">Source:</span> {{ userInfo.source }}</div>
                  </template>
                </Card>

                <div class="mt-5 ml-2" v-if="platformInfo.exists">
                  AI found similar platform in the Brain. Either use it, or create a new platform.
                </div>
                <div class="mt-5 ml-2" v-else>
                  AI did not find similar platform in the Brain. Either create a new platform, or fill in existing one.
                </div>

                <div class="flex gap-4">
                  <Card class="!bg-white !border !border-slate-200 !rounded-xl !mt-5 flex-1">
                    <template #content>
                      <div class="font-bold text-lg mb-2">New Platform</div>
                      <div class="flex flex-col gap-2">
                        <FloatLabel variant="on">
                          <InputText v-model="newPlatformInfo.name" />
                          <label for="on_label">Name</label>
                          <i
                            class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                            v-tooltip="'Full name of the platform'"
                          />
                        </FloatLabel>
                        <FloatLabel variant="on">
                          <InputText v-model="newPlatformInfo.short_name" />
                          <label for="on_label">Short Name</label>
                          <i
                            class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                            v-tooltip="'Short name of the platform, can be same as the full name'"
                          />
                        </FloatLabel>
                        <FloatLabel variant="on">
                          <InputText v-model="newPlatformInfo.provider" />
                          <label for="on_label">Provider</label>
                          <i
                            class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                            v-tooltip="'Provider of the platform, e.g. EBSCO, ProQuest, etc.'"
                          />
                        </FloatLabel>
                        <FloatLabel variant="on">
                          <InputText v-model="newPlatformInfo.url" />
                          <label for="on_label">URL</label>
                          <i
                            class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                            v-tooltip="'URL of the platform, must be valid URL starting with http...'"
                          />
                        </FloatLabel>
                        <Button
                          label="Create this platform"
                          @click="() => processPlatform(activateCallback, newPlatformInfo)"
                          severity="info"
                          class="self-start"
                          :disabled="
                            !newPlatformInfo.name ||
                            !newPlatformInfo.short_name ||
                            !newPlatformInfo.provider ||
                            !newPlatformInfo.url
                          "
                        />
                      </div>
                    </template>
                  </Card>
                  <Card class="!bg-white !border !border-slate-200 !rounded-xl !mt-5 flex-1">
                    <template #content>
                      <div class="font-bold text-lg mb-2">Existing Platform</div>
                      <a
                        :href="`https://brain.celus.net/admin/knowledgebase/platform/${existingPlatformInfo.pk}/change/`"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="text-blue-600 hover:underline"
                      >
                        Platform in Brain
                      </a>
                      <div class="flex flex-col gap-2 mt-2">
                        <FloatLabel variant="on">
                          <InputText v-model="existingPlatformInfo.name" />
                          <label for="on_label">Name</label>
                        </FloatLabel>
                        <FloatLabel variant="on">
                          <InputText v-model="existingPlatformInfo.short_name" />
                          <label for="on_label">Short Name</label>
                        </FloatLabel>
                        <FloatLabel variant="on">
                          <InputNumber v-model="existingPlatformInfo.pk" />
                          <label for="on_label">ID</label>
                          <i
                            class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                            v-tooltip="'ID of the platform in Brain'"
                          />
                        </FloatLabel>
                        <FloatLabel variant="on">
                          <InputText v-model="existingPlatformInfo.provider" />
                          <label for="on_label">Provider</label>
                        </FloatLabel>
                        <FloatLabel variant="on">
                          <InputText v-model="existingPlatformInfo.url" />
                          <label for="on_label">URL</label>
                        </FloatLabel>
                        <Button
                          label="Use existing platform"
                          @click="() => processPlatform(activateCallback, existingPlatformInfo)"
                          severity="info"
                          class="self-start"
                          :disabled="
                            !existingPlatformInfo.name || !existingPlatformInfo.short_name || !existingPlatformInfo.pk
                          "
                        />
                      </div>
                    </template>
                  </Card>
                </div>
              </div>
            </template>
            <template #footer>
              {{ platformError }}
            </template>
          </Card>
        </StepPanel>
      </StepItem>
      <StepItem value="2">
        <Step>Metrics,Dimensions,Report Type</Step>
        <StepPanel v-slot="{ activateCallback }">
          <Card style="width: 60rem; overflow: hidden">
            <template #title>Metrics,Dimensions,Report Type</template>
            <template #content>
              {{ dataDescriptionState }}
              <div class="data-description" v-if="dataDescriptionState == 'Finished'">
                <div style="padding-top: 10px; padding-bottom: 20px">
                  This is the data information received from the input file. Please modify it if you find any
                  discrepancies or if some metrics or dimensions are unnecessary. This information will be used to
                  generate the parsing rules.
                </div>

                <div class="!bg-white !border !border-slate-200 !rounded-xl p-6">
                  <Divider align="center" type="solid">
                    <b class="text-lg">Data File</b>
                  </Divider>
                  <div class="flex flex-col gap-2">
                    <div class="flex items-center gap-2">
                      <span>Start month year: </span>
                      <InputText id="begin_month_text" v-model="descriptionData.begin_month_year" />
                      <i
                        class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                        v-tooltip="'First full month in the data file'"
                      />
                    </div>
                    <div class="flex items-center gap-2">
                      <span>End month year: </span>
                      <InputText id="end_month_text" v-model="descriptionData.end_month_year" />
                      <i
                        class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                        v-tooltip="'Last full month in the data file'"
                      />
                    </div>

                    <div class="flex items-center gap-2">
                      <span>English: </span>
                      <Checkbox v-model="descriptionData.english" binary />
                      <i
                        class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                        v-tooltip="'Whether the data is in English'"
                      />
                      <span v-if="!descriptionData.english" class="pl-2 ml-2"
                        >Do you want to translate the data?
                        <Button label="Yes" @click="translateData" />
                      </span>
                      <div v-if="translations">Generated translations for metrics: {{ metricsTranslations }}</div>
                      <div v-if="translations">Generated translations for dimensions: {{ dimTranslations }}</div>
                    </div>
                    <div class="flex items-center gap-2">
                      <span>Granularity: </span>
                      <Select
                        id="granularity_select"
                        v-model="descriptionData.granularity"
                        :options="granularityOptions"
                        style="width: 250px"
                      />
                      <i
                        class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                        v-tooltip="'Data aggregation - we currently only support daily and monthly data'"
                      />
                    </div>

                    <div class="flex items-center gap-2">
                      <span>Title report:</span>
                      <Checkbox v-model="descriptionData.title_report" binary inputId="title_report_cb" />
                      <i
                        class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                        v-tooltip="'Does the file include information about titles?'"
                      />
                    </div>

                    <div v-if="descriptionData.title_report" class="flex items-center gap-2">
                      <FloatLabel variant="on">
                        <MultiSelect
                          id="identifiers_multiselect"
                          v-model="descriptionData.title_identifiers"
                          :options="titleIdentifierOptions"
                          style="width: 250px"
                        />
                        <label for="identifiers_multiselect">Title Identifiers</label>
                        <i
                          class="pi pi-info-circle ml-2 text-slate-400 cursor-help"
                          v-tooltip="
                            'Which identifiers are used for the titles? Proprietary is for any other identifiers.'
                          "
                        />
                      </FloatLabel>
                    </div>
                  </div>

                  <div style="padding-bottom: 10px">
                    <Divider align="center" type="solid">
                      <b class="text-lg">Metrics</b>
                    </Divider>

                    Here you can .... map
                    <DataTable
                      :value="descriptionData.metrics"
                      size="small"
                      stripedRows
                      style="width: 100%"
                      :tableStyle="{ tableLayout: 'fixed' }"
                      :emptyMessage="'No metrics yet'"
                    >
                      <Column header="File column,row" style="width: 14rem">
                        <template #body="{ data }">
                          <Select
                            class="cell-select-wrap"
                            :modelValue="data.data_metric"
                            @update:modelValue="(value) => (data.data_metric = value)"
                            :options="availableDataValues"
                            placeholder="Pick data metric/dimension"
                            appendTo="body"
                            scrollHeight="18rem"
                            :panelStyle="{ width: '28rem', maxWidth: 'calc(100vw - 2rem)' }"
                            filter
                            editable
                            filterPlaceholder="Search data columns/rows..."
                            style="width: 100%"
                          />
                        </template>
                      </Column>
                      <Column header="Brain metric">
                        <template #body="{ data }">
                          <Select
                            class="cell-select-wrap"
                            :modelValue="getBrainMetricShortName(data)"
                            @update:modelValue="(value) => setBrainMetricShortName(data, value)"
                            :options="brainMetricOptions"
                            optionLabel="label"
                            optionValue="value"
                            placeholder=""
                            appendTo="body"
                            scrollHeight="18rem"
                            :panelStyle="{ width: '28rem', maxWidth: 'calc(100vw - 2rem)' }"
                            filter
                            editable
                            filterBy="label"
                            filterPlaceholder="Search brain metrics or type custom name..."
                            style="width: 100%"
                          />
                        </template>
                      </Column>
                      <Column header="Interest Group">
                        <template #body="{ data }">
                          <Select
                            class="cell-select-wrap"
                            v-model="data.interest_group"
                            :options="interestGroupOptions"
                            optionLabel="label"
                            optionValue="value"
                            placeholder=""
                            appendTo="body"
                            scrollHeight="18rem"
                            :panelStyle="{ width: '20rem', maxWidth: 'calc(100vw - 2rem)' }"
                            filter
                            filterBy="label"
                            filterPlaceholder="Search interest groups..."
                            style="width: 100%"
                          />
                        </template>
                      </Column>
                      <Column header="" style="width: 4rem">
                        <template #body="{ data }">
                          <Button icon="pi pi-times" severity="info" text @click="() => deleteMetricRow(data)" />
                        </template>
                      </Column>
                    </DataTable>
                    <div style="padding-top: 8px">
                      <Button icon="pi pi-plus" label="Add" severity="secondary" @click="addMetricRow" />
                    </div>
                  </div>
                  <div style="padding-bottom: 10px">
                    <Divider align="center" type="solid">
                      <b class="text-lg">Dimensions</b>
                    </Divider>
                    Here you can .... map
                    <DataTable
                      :value="descriptionData.dimensions"
                      size="small"
                      stripedRows
                      style="width: 100%"
                      :tableStyle="{ tableLayout: 'fixed' }"
                      :emptyMessage="'No dimensions yet'"
                    >
                      <Column header="File column,row" style="width: 14rem">
                        <template #body="{ data }">
                          <Select
                            class="cell-select-wrap"
                            :modelValue="data.data_dimension"
                            @update:modelValue="(value) => (data.data_dimension = value)"
                            :options="availableDataValues"
                            placeholder=""
                            appendTo="body"
                            scrollHeight="18rem"
                            :panelStyle="{ width: '20rem', maxWidth: 'calc(100vw - 2rem)' }"
                            filter
                            editable
                            filterPlaceholder="Search data metric/dimension..."
                            style="width: 100%"
                          />
                        </template>
                      </Column>
                      <Column header="Brain dimension">
                        <template #body="{ data }">
                          <Select
                            class="cell-select-wrap"
                            :modelValue="getBrainDimensionShortName(data)"
                            @update:modelValue="(value) => setBrainDimensionShortName(data, value)"
                            :options="brainDimensionOptions"
                            optionLabel="label"
                            optionValue="value"
                            placeholder=""
                            appendTo="body"
                            scrollHeight="18rem"
                            :panelStyle="{ width: '28rem', maxWidth: 'calc(100vw - 2rem)' }"
                            filter
                            editable
                            filterBy="label"
                            filterPlaceholder="Search brain dimensions or type custom name..."
                            style="width: 100%"
                          />
                        </template>
                      </Column>
                      <Column header="" style="width: 4rem">
                        <template #body="{ data }">
                          <Button icon="pi pi-times" severity="info" text @click="() => deleteDimensionRow(data)" />
                        </template>
                      </Column>
                    </DataTable>
                    <div style="padding-top: 8px">
                      <Button icon="pi pi-plus" label="Add" severity="secondary" @click="addDimensionRow" />
                    </div>
                  </div>
                  <Divider />
                  <div>
                    <Button severity="info" label="Submit Data" @click="() => submitMetricsAndDimensions()" />
                    <Button
                      severity="info"
                      label="Proceed to Parsing"
                      @click="() => generateParsingRules(activateCallback)"
                    />
                  </div>
                </div>
              </div>
            </template>
          </Card>
        </StepPanel>
      </StepItem>
      <StepItem value="3">
        <Step>Parsing, Output</Step>
        <StepPanel v-slot="{ activateCallback }">
          <Card style="width: 60rem; overflow: hidden">
            <template #content>
              <div v-if="parsingRulesState == 'loading'">
                <div class="mb-3">Generating parsing rules, please wait...</div>
                <div class="mb-2">
                  <div class="text-sm text-gray-600 mb-1">
                    Progress: {{ parsingProgress.current }} / {{ parsingProgress.total }}
                  </div>
                  <div class="w-full bg-gray-200 rounded-full h-2.5">
                    <div
                      class="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                      :style="{ width: `${(parsingProgress.current / parsingProgress.total) * 100}%` }"
                    ></div>
                  </div>
                </div>
                <div class="text-sm text-gray-500">{{ parsingProgress.message }}</div>
              </div>
              <div v-if="parsingRulesState == 'done'">These are parsing rules generated by the model.</div>
              <div v-if="parsingRulesState == 'failed'">
                Parsing rules generation failed. Please retry from the Data Description step.
              </div>
              <div>
                <Textarea v-model="parsingRules" autoResize rows="10" cols="55" />
              </div>
              <div class="py-6">
                <Button label="Back" severity="secondary" @click="activateCallback('2')" />
              </div>
              <DataTable :value="rows">
                <Column
                  v-for="col in columns"
                  :key="col.field"
                  :field="col.field"
                  size="small"
                  :header="col.header"
                /> </DataTable
            ></template>
          </Card>
        </StepPanel>
      </StepItem>
    </Stepper>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import FloatLabel from 'primevue/floatlabel'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Checkbox from 'primevue/checkbox'
import Stepper from 'primevue/stepper'
import StepItem from 'primevue/stepitem'
import Step from 'primevue/step'
import StepPanel from 'primevue/steppanel'
import Divider from 'primevue/divider'


import {
  axios_client,
  getState,
  setState,
  callWorker,
  callWorkerWithProgress,
  getBrainMetrics,
  getBrainDimensions,
  extractErrorMessage,
  startSession,
} from './api'
import type { BrainMetric, BrainDimension, MetricMapping, DimensionMapping, ProgressUpdate } from './api'

const sessionId = ref<number>(0)
const dataDescriptionState = ref('') //'', 'loading', 'done'
const parsingRulesState = ref('') //'', 'loading', 'done'
const fetchingIssueStatus = ref('') //'', 'loading', 'done'
const stepNumber = ref(1)

interface PlatformData {
  name: string
  short_name: string
  provider: string
  url: string
  exists: boolean
  pk: number | null
}

interface UserInfoData {
  user_comment: string | null
  gitlab_issue: number | null
  source: string | null
}

const userInfo = ref<UserInfoData>({
  user_comment: null,
  gitlab_issue: null,
  source: null,
})

const platformInfo = reactive<PlatformData>({
  name: '',
  provider: '',
  short_name: '',
  url: '',
  exists: false,
  pk: null,
})

const newPlatformInfo = reactive<PlatformData>({
  name: '',
  provider: '',
  short_name: '',
  url: '',
  exists: false,
  pk: null,
})

const existingPlatformInfo = reactive<PlatformData>({
  name: '',
  provider: '',
  short_name: '',
  url: '',
  exists: true,
  pk: 0,
})

const platformError = ref('')
const file = ref<File | null>(null)
const selectedFileName = ref('')
const gitlabIssueUrl = computed(() =>
  userInfo.value.gitlab_issue ? `https://gitlab.com/big-dig-data/celus/-/issues/${userInfo.value.gitlab_issue}` : '',
)

const titleIdentifierOptions: string[] = ['Print_ISSN', 'Online_ISSN', 'ISBN', 'DOI', 'URI', 'Proprietary']
const granularityOptions: string[] = ['daily', 'monthly', 'other']

const interestGroupOptions = [
  { label: 'Full Text', value: 'full_text' },
  { label: 'Search', value: 'search' },
  { label: 'Full Text Denial', value: 'full_text_denial' },
  { label: 'Search Denial', value: 'search_denial' },
  { label: 'Other', value: 'other' },
  { label: 'Multimedia', value: 'multimedia' },
]

const parsingRules = ref('') // JSON string of the parsing rules

type ParsedDataColumn = { field: string; header: string }
const columns = ref<ParsedDataColumn[]>([]) // columns of the parsed data (from backend)
const rows = ref<Record<string, any>[]>([]) // rows of the parsed data (array of objects)

// Progress tracking for parsing rules generation
const parsingProgress = ref({ current: 0, total: 10, message: '' })

const translations = ref(false) //whether to translate the data
const dimTranslations = ref([])
const metricsTranslations = ref([])

interface DataDescriptionData {
  begin_month_year: string
  end_month_year: string
  english: boolean
  title_report: boolean
  item_report: boolean
  organization: string | null
  granularity: string
  title_identifiers: string[]
  metrics: MetricMapping[]
  dimensions: DimensionMapping[]
}

const descriptionData = reactive<DataDescriptionData>({
  begin_month_year: '',
  end_month_year: '',
  english: false,
  title_report: false,
  item_report: false,
  organization: null,
  granularity: '',
  title_identifiers: [],
  metrics: [],
  dimensions: [],
})

// Auto-incrementing ID counter for table rows (frontend only)
let nextRowId = 0

// Available options for dropdown (union of metrics and dimensions from file)
// This is a fixed set that doesn't change when rows are deleted
const availableDataValues = ref<string[]>([])

const brainMetrics = ref<BrainMetric[]>([])
const brainMetricOptions = computed(() =>
  (brainMetrics.value || []).map((m) => ({
    label: m.toDisplay(),
    value: m.short_name,
  })),
)

const brainDimensions = ref<BrainDimension[]>([])
const brainDimensionOptions = computed(() =>
  (brainDimensions.value || []).map((d) => ({
    label: d.toDisplay(),
    value: d.short_name,
  })),
)

// JSON.stringify replacer can't reliably remove nulls inside arrays (they become `null`),
// so we deep-clean the object first, then stringify the cleaned object.
const deepOmitNulls = (value: any): any => {
  if (value === null) return undefined
  if (Array.isArray(value)) {
    const cleaned = value.map((v) => deepOmitNulls(v)).filter((v) => v !== undefined)
    return cleaned.length === 0 ? undefined : cleaned
  }
  if (typeof value === 'object' && value) {
    const out: Record<string, any> = {}
    for (const [k, v] of Object.entries(value)) {
      const cleaned = deepOmitNulls(v)
      if (cleaned !== undefined) out[k] = cleaned
    }
    // if object became empty, omit it too
    return Object.keys(out).length === 0 ? undefined : out
  }
  return value
}

// Helper functions to get/set brain metric short_name for UI
const getBrainMetricShortName = (mapping: MetricMapping): string => {
  return mapping.brain_metric?.short_name || ''
}

const setBrainMetricShortName = (mapping: MetricMapping, shortName: string) => {
  if (shortName) {
    const brainMetric = brainMetrics.value.find((m) => m.short_name === shortName)
    if (brainMetric) {
      // Found existing metric - use full object with real id
      mapping.brain_metric = brainMetric
    } else {
      // Custom name - create object with id: 0 as sentinel for "create new"
      mapping.brain_metric = { id: 0, short_name: shortName, aliases: [] } as any
    }
  } else {
    mapping.brain_metric = null
  }
}

// Helper functions to get/set brain dimension short_name for UI
const getBrainDimensionShortName = (mapping: DimensionMapping): string => {
  return mapping.brain_dimension?.short_name || ''
}

const setBrainDimensionShortName = (mapping: DimensionMapping, shortName: string) => {
  if (shortName) {
    const brainDimension = brainDimensions.value.find((d) => d.short_name === shortName)
    if (brainDimension) {
      // Found existing dimension - use full object with real id
      mapping.brain_dimension = brainDimension
    } else {
      // Custom name - create object with id: 0 as sentinel for "create new"
      mapping.brain_dimension = { id: 0, short_name: shortName, aliases: [] } as any
    }
  } else {
    mapping.brain_dimension = null
  }
}

// Simple add/delete functions for metric mappings
const addMetricRow = () => {
  const newMapping: MetricMapping = {
    id: nextRowId++,
    data_metric: '',
    brain_metric: null,
    interest_group: null,
  }
  descriptionData.metrics.push(newMapping)
}

const deleteMetricRow = (mapping: MetricMapping) => {
  const index = descriptionData.metrics.indexOf(mapping)
  if (index > -1) {
    descriptionData.metrics.splice(index, 1)
  }
}

// Simple add/delete functions for dimension mappings
const addDimensionRow = () => {
  const newMapping: DimensionMapping = {
    id: nextRowId++,
    data_dimension: '',
    brain_dimension: null,
  }
  descriptionData.dimensions.push(newMapping)
}

const deleteDimensionRow = (mapping: DimensionMapping) => {
  const index = descriptionData.dimensions.indexOf(mapping)
  if (index > -1) {
    descriptionData.dimensions.splice(index, 1)
  }
}

const generateParsingRules = async (activateCallback: (step: string) => void) => {
  parsingRulesState.value = 'loading'
  parsingRules.value = ''
  parsingProgress.value = { current: 0, total: 10, message: 'Starting...' }
  activateCallback('3')
  console.log('Generating parsing rules for platform:', platformInfo.name)

  try {
    await callWorkerWithProgress(sessionId.value, 'parsing_rules_worker', (progress: ProgressUpdate) => {
      parsingProgress.value = {
        current: progress.current,
        total: progress.total,
        message: progress.message,
      }
      console.log('Progress:', progress)
    })

    const newParsingRules = await getState(sessionId.value, 'parser_definition_data')
    if (newParsingRules == null) {
      parsingRulesState.value = 'failed'
      return
    }
    parsingRules.value = JSON.stringify(deepOmitNulls(newParsingRules), null, 3)
    parsingRulesState.value = 'done'
    const parsedData = await getState(sessionId.value, 'parsed_data')
    columns.value = parsedData.columns
    rows.value = parsedData.rows
    console.log('Parsed data:', parsedData)
  } catch (error) {
    console.error('Error generating parsing rules:', error)
    parsingRulesState.value = 'failed'
  }
}

const processPlatform = async (activateCallback: (step: string) => void, platformData: PlatformData) => {
  platformError.value = ''
  dataDescriptionState.value = 'Processing the platform...'
  // go to second step in stepper
  console.log('Processing platform:', platformData.name)

  // update platform data
  console.log('Updating platform data:', platformData)
  try {
    await setState(sessionId.value, 'user_info_data', { ...userInfo.value })
    await setState(sessionId.value, 'platform_data', { ...platformData })
    //dunno about the file
    await axios_client.get(`submit_platform/${sessionId.value}`) //submit platform to gitlab
    activateCallback('2')
  } catch (error) {
    console.error('Error submitting platform:', error)
    platformError.value = extractErrorMessage(error)
    dataDescriptionState.value = 'Failed to process the platform.'
  }

  await generateDescription()
}

const submitMetricsAndDimensions = async () => {
  // Backend expects snake_case keys and nested BrainMetric/BrainDimension objects (or null).
  // Remove frontend-only id fields before sending to backend

  //update data description data
  await setState(sessionId.value, 'data_description_data', descriptionData)
  //update metrics dimensions data
  const payload = {
    metrics: descriptionData.metrics.map(({ id, ...m }) => ({
      data_metric: m.data_metric,
      brain_metric: m.brain_metric
        ? { id: m.brain_metric.id, short_name: m.brain_metric.short_name, aliases: m.brain_metric.aliases }
        : null,
      interest_group: m.interest_group || null,
    })),
    dimensions: descriptionData.dimensions.map(({ id, ...d }) => ({
      data_dimension: d.data_dimension,
      brain_dimension: d.brain_dimension
        ? { id: d.brain_dimension.id, short_name: d.brain_dimension.short_name, aliases: d.brain_dimension.aliases }
        : null,
    })),
  }

  await setState(sessionId.value, 'metrics_dimensions_data', payload)
  await axios_client.post(`submit_metrics_dimensions/${sessionId.value}`)
  const newMetricsDimensions = await getState(sessionId.value, 'metrics_dimensions_data')
  console.log('Metrics and dimensions:', newMetricsDimensions)
}

const fillFromGitlab = async () => {
  if (!userInfo.value.gitlab_issue) {
    console.error('No GitLab issue number provided')
    fetchingIssueStatus.value = 'No Gitlab issue number provided.'
    return
  }
  fetchingIssueStatus.value = 'Processing the issue...'
  console.log('Filling platform info from GitLab issue:', userInfo.value.gitlab_issue)

  // Update user_info_data with both comment and GitLab issue number
  await setState(sessionId.value, 'user_info_data', { ...userInfo.value })

  // Call Gitlab worker to fetch platform info from the issue
  await callWorker(sessionId.value, 'gitlab_worker')

  // Read platform_data returned by the worker and use it as in processPlatform
  const newPlatformData = await getState(sessionId.value, 'platform_data')
  console.log('Platform data from GitLab:', newPlatformData)
  Object.assign(platformInfo, newPlatformData)
  fetchingIssueStatus.value = 'Finished'

  if (platformInfo.exists) {
    console.log('Using existing platform:', existingPlatformInfo)
    Object.assign(existingPlatformInfo, platformInfo)
  } else {
    console.log('Creating new platform:', newPlatformInfo)
    Object.assign(newPlatformInfo, platformInfo)
  }

  // Also check if file_data is available (it might have been set by the worker)
  const fileData = await getState(sessionId.value, 'file_data')
  if (fileData && fileData.file_name) {
    console.log('File data from GitLab:', fileData)
    // IMPORTANT: don't create a dummy File and upload it, it would overwrite the real file
    // downloaded by the backend GitLab worker. We only use this for display.
    selectedFileName.value = fileData.file_name
    file.value = null
    fetchingIssueStatus.value = 'Finished, File downloaded succesfully'
  }

  userInfo.value = await getState(sessionId.value, 'user_info_data')
  console.log('User info from GitLab:', userInfo)

  stepNumber.value = 2
}

const generateDescription = async () => {
  dataDescriptionState.value = 'Generating the data description from the input file...'
  await callWorker(sessionId.value, 'data_description_worker')
  const newDataDescription = await getState(sessionId.value, 'data_description_data')
  dataDescriptionState.value = 'Finished, Data description generated'
  // Store the fixed set of available data values before any modifications
  const metricNames = (newDataDescription.metrics || []).map((m: MetricMapping) => m.data_metric)
  const dimensionNames = (newDataDescription.dimensions || []).map((d: DimensionMapping) => d.data_dimension)
  availableDataValues.value = [...new Set([...metricNames, ...dimensionNames])]

  // Assign all fields including metrics and dimensions
  Object.assign(descriptionData, newDataDescription)

  dataDescriptionState.value = 'Finished'
}

const translateData = async () => {
  translations.value = true
  await callWorker(sessionId.value, 'translation_worker')
  const newTranslations = await getState(sessionId.value, 'translation_data')
  metricsTranslations.value = newTranslations.metrics_translations
  dimTranslations.value = newTranslations.dimensions_translations
}

onMounted(async () => {
  try {
    const response = await startSession()
    if (!response) {
      console.error('Failed to start session: no response')
      return
    }
    sessionId.value = response.session_id
    const metrics = await getBrainMetrics()
    brainMetrics.value = metrics || []
    const dims = await getBrainDimensions()
    brainDimensions.value = dims || []
  } catch (error) {
    console.error('Failed to start session:', error)
  }
})
</script>

<style scoped>
.container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  margin-top: 20px;
}

/* Prevent long Select labels from expanding the table; wrap to multiple lines instead */
:deep(.p-datatable td) {
  min-width: 0;
}

:deep(.cell-select-wrap) {
  min-width: 0;
  max-width: 100%;
}

:deep(.cell-select-wrap .p-select-label) {
  white-space: normal !important;
  overflow: visible !important;
  text-overflow: clip !important;
  overflow-wrap: anywhere;
  word-break: break-word;
  line-height: 1.2;
}
.input-box {
  width: 300px;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.p-multiselect {
  min-width: 17rem;
  max-width: 400px;
}

.input-card-content {
  display: flex;
  gap: 1.5rem;
  align-items: flex-start;
}

.input-card-left,
.input-card-right {
  flex: 1;
}

.input-card-divider {
  width: 1px;
  align-self: stretch;
  background-color: #e0e0e0;
}

.helper-text {
  color: #6b7280;
  font-size: 0.8rem;
}
</style>
