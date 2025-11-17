<template>
  <div>session id: {{ sessionId }}</div>
  <div class="container">
    <Stepper value="1">
      <StepItem value="1">
        <Step>Input Information</Step>
        <StepPanel v-slot="{ activateCallback }">
          <Card style="width: 40rem; overflow: hidden">
            <template #title>Input Information</template>
            <template #subtitle
              >Please fill in the information from the customer - platform name, the received file
              and any comments he provided.</template
            >
            <template #content>
              <div style="padding-bottom: 10px">
                <FloatLabel variant="on">
                  <InputText id="on_label" v-model="platform" style="width: 300px" />
                  <label for="on_label">Platform Name</label>
                </FloatLabel>
              </div>
              <div style="padding-bottom: 10px">
                <FloatLabel variant="on">
                  <Textarea
                    id="over_label"
                    v-model="userComment"
                    rows="5"
                    cols="30"
                    style="resize: none"
                  />
                  <label for="on_label">User Comments</label>
                </FloatLabel>
              </div>
              <FileUpload
                ref="fileupload"
                mode="basic"
                name="file"
                :maxFileSize="1000000"
                @select="onFileSelect"
                chooseLabel="CSV File"
                accept="text/csv"
                style="justify-content: left; display: block"
              />
            </template>
            <template #footer>
              <div style="padding-top: 30px">
                <Button label="Process Platform" @click="() => processPlatform(activateCallback)" />
              </div>
            </template>
          </Card>
        </StepPanel>
      </StepItem>
      <StepItem value="2">
        <Step>Data Description</Step>
        <StepPanel v-slot="{ activateCallback }">
          <Card style="width: 40rem; overflow: hidden">
            <template #content>
              <div v-if="platformState == 'loading'">
                Fetching information about {{ platform }}. Please wait...
              </div>
              <div v-if="platformState == 'new'">
                The platform {{ platform }} does not yet exist. Do you want me to process it?
                <div style="padding-top: 10px">
                  <Button label="Yes" @click="generateDescription" />
                </div>
              </div>
              <div v-if="platformState == 'old'">
                <!-- depends if there are parsers ocr not -->
                The platform {{ platform }} was found in the database, with the following parsers:
                {{ availableParsers }}. Do you want me to process it anyways?
                <div style="padding-top: 10px">
                  <Button label="Yes" @click="generateDescription" />
                </div>
              </div>
              <div v-if="dataDescriptionState == 'loading'">
                Generating Data Description, please wait...
              </div>
              <div class="data-description" v-if="dataDescriptionState == 'done'">
                <div style="font-weight: bold">Generated Data Description</div>
                <div style="padding-top: 10px; padding-bottom: 20px">
                  This is the data information received from the input file. Please modify it if you
                  find any discrepancies or if some metrics or dimensions are unnecessary. This
                  information will be used to generate the parsing rules.
                </div>

                <div style="padding-bottom: 10px">
                  <FloatLabel variant="on">
                    <InputText id="begin_month_text" v-model="descriptionData.begin_month_year" />
                    <label for="begin_month_text">Start Month Year</label>
                  </FloatLabel>
                </div>
                <div style="padding-bottom: 10px">
                  <FloatLabel variant="on">
                    <InputText id="end_month_text" v-model="descriptionData.end_month_year" />
                    <label for="end_month_text">End Month Year</label>
                  </FloatLabel>
                </div>

                <div class="flex items-center gap-2" style="padding-bottom: 10px">
                  <span>English: </span>
                  <ToggleButton
                    v-model="descriptionData.english"
                    onLabel="Yes"
                    offLabel="No"
                    onIcon="pi pi-lock"
                    offIcon="pi pi-lock-open"
                    size="small"
                    style="width: 100px"
                  />
                  <span v-if="!descriptionData.english" class="pl-2 ml-2"
                    >Do you want to translate the data?
                    <Button label="Yes" @click="translateData" />
                  </span>
                  <div v-if="translations">
                    Generated translations for metrics: {{ metricsTranslations }}
                  </div>
                  <div v-if="translations">
                    Generated translations for dimensions: {{ dimTranslations }}
                  </div>
                </div>

                <div class="flex items-center gap-2" style="padding-bottom: 10px">
                  <span>Title report: </span>
                  <ToggleButton
                    v-model="descriptionData.title_report"
                    onLabel="Yes"
                    offLabel="No"
                    onIcon="pi pi-lock"
                    offIcon="pi pi-lock-open"
                    size="small"
                    style="width: 100px"
                  />
                </div>
                <div style="padding-bottom: 10px">
                  <FloatLabel variant="on">
                    <MultiSelect
                      id="identifiers_multiselect"
                      v-model="descriptionData.title_identifiers"
                      :options="titleIdentifierOptions"
                      style="width: 250px"
                    />
                    <label for="identifiers_multiselect">Title Identifiers</label>
                  </FloatLabel>
                </div>
                <div style="padding-bottom: 10px">
                  <FloatLabel variant="on">
                    <Select
                      id="granularity_select"
                      v-model="descriptionData.granularity"
                      :options="granularityOptions"
                      style="width: 250px"
                    />
                    <label for="granularity_select">Granularity</label>
                  </FloatLabel>
                </div>
                <div style="padding-bottom: 10px">
                  <FloatLabel variant="on">
                    <MultiSelect
                      id="metrics_multiselect"
                      v-model="descriptionData.metrics"
                      :options="metricsDimensionsUnion.value"
                      display="chip"
                    />
                    <label for="metrics_multiselect">Metrics</label>
                  </FloatLabel>
                </div>
                <div style="padding-bottom: 10px">
                  <FloatLabel variant="on">
                    <MultiSelect
                      id="dimensions_multiselect"
                      v-model="descriptionData.dimensions"
                      :options="metricsDimensionsUnion.value"
                      display="chip"
                      style="width: 250px"
                    />
                    <label for="dimensions_multiselect">Dimensions</label>
                  </FloatLabel>
                </div>
              </div>
            </template>
            <template #footer>
              <div v-if="dataDescriptionState == 'done'">
                Please make changes if needed. Do you want to use this data description to generate
                the parsing rules?
                <div>
                  <Button
                    label="Generate Parsing Rules"
                    @click="() => generateParsingRules(activateCallback)"
                  />
                </div>
              </div>
            </template>
          </Card>
        </StepPanel>
      </StepItem>
      <StepItem value="3">
        <Step>Parsing Rules</Step>
        <StepPanel v-slot="{ activateCallback }">
          <Card style="width: 40rem; overflow: hidden">
            <template #content>
              <div v-if="parsingRulesState == 'loading'">
                Generating parsing rules, please wait...
              </div>
              <div v-if="parsingRulesState == 'done'">
                These are parsing rules generated by the model.
              </div>
              <div v-if="parsingRulesState == 'failed'">
                Parsing rules generation failed. Please retry from the Data Description step.
              </div>
              <div>
                <Textarea v-model="parsingRules" autoResize rows="10" cols="55" /></div
            ></template>
          </Card>
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
            />
          </DataTable>
        </StepPanel>
      </StepItem>
    </Stepper>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import axios from 'axios'
import InputText from 'primevue/inputtext'
import FloatLabel from 'primevue/floatlabel'
import Textarea from 'primevue/textarea'
import FileUpload from 'primevue/fileupload'
import Button from 'primevue/button'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import ToggleButton from 'primevue/togglebutton'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

import Stepper from 'primevue/stepper'
import StepItem from 'primevue/stepitem'
import Step from 'primevue/step'
import StepPanel from 'primevue/steppanel'

import { axios_client, getState, setState, callWorker } from './api'

const platformState = ref('') //'', 'new', 'old', 'loading'
const availableParsers = ref([]) //list of parsers available for the platform
const dataDescriptionState = ref('') //'', 'loading', 'done'
const parsingRulesState = ref('') //'', 'loading', 'done'

const platform = ref('') //user input - name of the platform
const userComment = ref('') //user input - any comment
const file = ref(null)

const sessionId = ref('')

const titleIdentifierOptions = ['Print_ISSN', 'Online_ISSN', 'ISBN', 'DOI', 'URI', 'Proprietary']
const granularityOptions = ['daily', 'monthly', 'other']

const metricsDimensionsUnion = []

const parsingRules = ref('')

const columns = ref([])
const rows = ref([])

const translations = ref(false)
const dimTranslations = ref([])
const metricsTranslations = ref([])

const descriptionData = reactive({
  begin_month_year: '',
  end_month_year: '',
  english: null,
  title_report: null,
  granularity: null,
  title_identifiers: null,
  metrics: null,
  dimensions: null,
})

const generateParsingRules = async (activateCallback) => {
  parsingRulesState.value = 'loading'
  parsingRules.value = ''
  activateCallback('3')
  console.log('Generating parsing rules for platform:', platform.value)
  await setState(sessionId.value, 'data_description_data', descriptionData)
  await callWorker(sessionId.value, 'parsing_rules_worker')
  const newParsingRules = await getState(sessionId.value, 'parser_definition_data')
  if(newParsingRules == null) {
    parsingRulesState.value = 'failed'
    return
  }
  parsingRules.value = JSON.stringify(newParsingRules, null, 3)
  parsingRulesState.value = 'done'
  const parsedData = await getState(sessionId.value, 'parsed_data')
  columns.value = parsedData.columns
  rows.value = parsedData.rows
  console.log('Parsed data:', parsedData)
}

const onFileSelect = (event) => {
  console.log('File selected:', event.files[0])
  file.value = event.files[0] // Store the selected file
}

const processPlatform = async (activateCallback) => {
  platformState.value = 'loading'
  activateCallback('2') // go to second step in stepper
  console.log('Processing platform:', platform.value)

  await setState(sessionId.value, 'user_info_data', {
    user_comment: userComment.value,
  })

  await setState(sessionId.value, 'platform_data', {
    platform_name: platform.value,
    exists: false,
    parser_names: [],
  })

  await callWorker(sessionId.value, 'platform_worker')

  const newPlatformData = await getState(sessionId.value, 'platform_data')
  if (newPlatformData.exists) {
    platformState.value = 'old'
    console.log('New platform data:', newPlatformData)
    availableParsers.value = newPlatformData.parser_names
  } else {
    platformState.value = 'new'
  }

  sendFile()
}

const sendFile = async () => {
  if (!file.value) {
    console.error('No file selected')
    return
  }

  const formData = new FormData()
  formData.append('file', file.value)

  try {
    const response = await axios_client.post(`upload_file/${sessionId.value}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  } catch (error) {
    console.error('Error uploading file:', error)
  }
}

const generateDescription = async () => {
  dataDescriptionState.value = 'loading'
  await callWorker(sessionId.value, 'data_description_worker')
  const newDataDescription = await getState(sessionId.value, 'data_description_data')
  Object.assign(descriptionData, newDataDescription)
  metricsDimensionsUnion.value = [
    ...new Set([...descriptionData.metrics, ...descriptionData.dimensions]),
  ]

  dataDescriptionState.value = 'done'
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
    const response = await axios.post('http://127.0.0.1:8000/start_session')
    sessionId.value = response.data.session_id
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
.input-box {
  width: 300px;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
.send-button {
  padding: 8px 16px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.send-button:hover {
  background-color: #0056b3;
}

.p-multiselect {
  min-width: 17rem;
  max-width: 400px;
}
</style>
