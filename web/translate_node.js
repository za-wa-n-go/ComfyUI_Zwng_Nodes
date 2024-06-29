import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { makeModal } from "./utils.js";

const findWidget = (node, name, attr = "name", func = "find") =>
  node.widgets[func]((w) => w[attr] === name);

function manual_translate_prompt() {
  const node = this,
    // Widgets
    button_manual_translate = findWidget(node, "Manual Translate"),
    widget_from_translate = findWidget(node, "from_translate"),
    widget_to_translate = findWidget(node, "to_translate"),
    manual_translate = findWidget(node, "manual_translate"),
    widget_textmultiline = findWidget(node, "text", "name");

  button_manual_translate.callback = async function () {
    if (!manual_translate.value) {
      makeModal({
        title: "Info",
        text: "<p>Manual translate disabled!</p><p>The translation works when you start generating images.</p>",
      });

      return;
    }

    try {
      let responseData = await api.fetchApi("/zwng/translate_manual", {
        method: "POST",
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          prompt: widget_textmultiline.value,
          srcTrans: widget_from_translate.value,
          toTrans: widget_to_translate.value,
        }),
      });

      console.log("Request sent to /zwng/translate_manual with data:", {
        prompt: widget_textmultiline.value,
        srcTrans: widget_from_translate.value,
        toTrans: widget_to_translate.value,
      });

      if (responseData.status !== 200) {
        console.error(
          "Error [" + responseData.status + "] > " + responseData.statusText
        );
        return;
      }

      responseData = await responseData.json();
      if (!responseData || responseData == undefined) {
        console.error("Error: translation not returned!");
        return;
      }

      if (responseData.hasOwnProperty("translate_prompt")) {
        widget_textmultiline.value = responseData.translate_prompt;
      }
    } catch (e) {
      console.error("Error during translation request:", e);
    }
  };
  button_manual_translate?.callback();
}

app.registerExtension({
  name: "Comfy.TranslateNode.Zwng",
  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    // --- TranslateNode
    if (
      nodeData.name == "ZwngSimpleGoogleTranslater" ||
      nodeData.name == "ZwngTranslateCLIPTextEncodeNode"
    ) {
      // Node Created
      const onNodeCreated = nodeType.prototype.onNodeCreated;
      nodeType.prototype.onNodeCreated = function () {
        onNodeCreated?.apply?.(this, arguments);
        const node = this,
          TranslateNode = app.graph._nodes.filter(
            (wi) => wi.type == nodeData.name
          ),
          nodeName = `${nodeData.name}_${TranslateNode.length}`;

        console.log(`Create ${nodeData.name}: ${nodeName}`);

        node.addWidget(
          "button",
          "Manual Translate",
          "Manual Translate",
          manual_translate_prompt.bind(node)
        );

        const manualTranslateWidget = findWidget(node, "manual_translate");
        manualTranslateWidget.type = "toggle";
        manualTranslateWidget.value = false;
        node.widgets.splice(node.widgets.indexOf(manualTranslateWidget) + 1, 0, node.widgets.pop());
      };

      // Node Configure
      const onConfigure = nodeType.prototype.onConfigure;
      nodeType.prototype.onConfigure = function () {
        onConfigure?.apply(this, arguments);

        if (this?.widgets_values.length) {
          if (typeof this.widgets_values[2] === "string") {
            const customtext = findWidget(this, "text", "name", "findIndex");
            this.widgets[customtext].value = this.widgets_values[2];
            this.widgets[2].value = false;
          }
        }
      };
    }

    // --- TranslateNode
  },
});
