pragma ComponentBehavior: Bound
import QtQuick
import qs.Commons

// Monzo Glance's second view: the Monzo account itself — balance, spent today, with pots, the pots, and
// the last seven days of transactions.
//
// Like HoverCard.qml, every string here is a whole field from the engine (`model.build_account`).
// This file does no arithmetic on money and builds no text; its only sums are pixels, and its
// only decision is how tall the scrolling transaction list is allowed to get.
Item {
  id: ac

  property var doc: null                 // the engine's `account` object, or null
  property var host: null                // BarWidget (kept for symmetry with HoverCard)
  property color foreground: Color.foreground
  property string fontFamily: Style.font.family

  signal openRequested()

  readonly property color muted: Qt.darker(foreground, 1.4)
  readonly property color faint: Qt.darker(foreground, 1.9)
  readonly property var balances: doc && doc.balances ? doc.balances : []
  readonly property var pots: doc && doc.pots ? doc.pots : []
  readonly property var days: doc && doc.days ? doc.days : []

  width: parent ? parent.width : Style.space(428)
  implicitHeight: body.implicitHeight

  Column {
    id: body
    width: parent.width
    spacing: Style.space(6)

    // ---- balance: the account's own figure, with spent today and the balance with pots
    Repeater {
      model: ac.balances

      Item {
        required property var modelData
        width: parent.width
        height: labelRow.implicitHeight + (modelData.sub_text !== "" ? subText.implicitHeight + Style.space(2) : 0)

        Item {
          id: labelRow
          width: parent.width
          implicitHeight: Math.max(balLabel.implicitHeight, balValue.implicitHeight)

          Text {
            id: balLabel
            anchors.left: parent.left
            anchors.baseline: balValue.baseline
            textFormat: Text.PlainText
            text: modelData.label || ""
            color: ac.muted
            font.family: ac.fontFamily
            font.pixelSize: Style.font.body
          }

          Text {
            id: balValue
            anchors.right: parent.right
            textFormat: Text.PlainText
            text: modelData.value_text || ""
            color: ac.foreground
            font.family: ac.fontFamily
            font.pixelSize: Style.font.display
            font.bold: true
            font.features: ({ "tnum": 1 })
          }
        }

        Text {
          id: subText
          y: labelRow.implicitHeight + Style.space(2)
          width: parent.width
          textFormat: Text.PlainText
          text: modelData.sub_text || ""
          color: ac.muted
          font.family: ac.fontFamily
          font.pixelSize: Style.font.caption
          font.features: ({ "tnum": 1 })
          wrapMode: Text.Wrap
        }
      }
    }

    // ---- pots: one row each, as Monzo lists them
    Text {
      visible: text !== ""
      width: parent.width
      textFormat: Text.PlainText
      text: ac.doc ? (ac.doc.pots_label || "") : ""
      color: ac.faint
      font.family: ac.fontFamily
      font.pixelSize: Style.font.caption
      topPadding: Style.space(2)
    }

    Repeater {
      model: ac.pots

      Item {
        required property var modelData
        width: parent.width
        height: potName.implicitHeight + Style.space(5)

        Text {
          id: potName
          anchors.left: parent.left
          anchors.baseline: potValue.baseline
          textFormat: Text.PlainText
          text: modelData.name || ""
          color: ac.foreground
          font.family: ac.fontFamily
          font.pixelSize: Style.font.body
        }

        Text {
          id: potValue
          anchors.right: parent.right
          textFormat: Text.PlainText
          text: modelData.value_text || ""
          color: ac.foreground
          font.family: ac.fontFamily
          font.pixelSize: Style.font.body
          font.features: ({ "tnum": 1 })
        }
      }
    }

    Rectangle { width: parent.width; height: 1; color: Util.alpha(ac.foreground, 0.18); visible: ac.pots.length > 0 || ac.balances.length > 0 }

    // ---- the last seven days: a day's name, then its transactions, newest first.
    // A busy week is taller than the popup, so the list scrolls; nothing is hidden by a cap.
    Text {
      visible: text !== ""
      width: parent.width
      textFormat: Text.PlainText
      text: ac.doc ? (ac.doc.days_label || "") : ""
      color: ac.faint
      font.family: ac.fontFamily
      font.pixelSize: Style.font.caption
    }

    Flickable {
      id: txScroll
      visible: ac.days.length > 0
      width: parent.width
      height: Math.min(contentHeight, Style.space(330))
      contentHeight: daysColumn.implicitHeight
      clip: true
      boundsBehavior: Flickable.StopAtBounds
      interactive: contentHeight > height

      Column {
        id: daysColumn
        width: parent.width
        spacing: 0

        Repeater {
          model: ac.days

          Column {
            id: dayBlock
            required property var modelData
            width: parent.width
            spacing: 0

            Text {
              width: parent.width
              textFormat: Text.PlainText
              text: dayBlock.modelData.label || ""
              color: ac.muted
              font.family: ac.fontFamily
              font.pixelSize: Style.font.caption
              topPadding: Style.space(6)
              bottomPadding: Style.space(2)
            }

            Repeater {
              model: dayBlock.modelData.rows

              Item {
                id: txRow
                required property var modelData
                width: parent.width
                height: Math.max(txEmoji.implicitHeight, txTime.implicitHeight) + Style.space(6)

                Text {
                  id: txTime
                  anchors.left: parent.left
                  anchors.baseline: txName.baseline
                  textFormat: Text.PlainText
                  text: txRow.modelData.time_text || ""
                  color: ac.faint
                  font.family: ac.fontFamily
                  font.pixelSize: Style.font.caption
                  font.features: ({ "tnum": 1 })
                }

                Text {
                  id: txEmoji
                  anchors.left: txTime.right
                  anchors.leftMargin: Style.space(8)
                  anchors.baseline: txName.baseline
                  width: Style.space(20)
                  horizontalAlignment: Text.AlignHCenter
                  textFormat: Text.PlainText
                  text: txRow.modelData.emoji || ""
                  font.pixelSize: Style.font.subtitle
                }

                Text {
                  id: pendingTag
                  visible: txRow.modelData.pending === true
                  anchors.right: txAmount.left
                  anchors.rightMargin: Style.space(8)
                  anchors.baseline: txName.baseline
                  textFormat: Text.PlainText
                  text: "pending"
                  color: ac.faint
                  font.family: ac.fontFamily
                  font.pixelSize: Style.font.caption
                  font.italic: true
                }

                Text {
                  id: txName
                  anchors.left: txEmoji.right
                  anchors.leftMargin: Style.space(4)
                  anchors.right: pendingTag.visible ? pendingTag.left : txAmount.left
                  anchors.rightMargin: Style.space(8)
                  textFormat: Text.PlainText
                  text: txRow.modelData.name || ""
                  color: ac.foreground
                  font.family: ac.fontFamily
                  font.pixelSize: Style.font.body
                  elide: Text.ElideRight
                }

                Text {
                  id: txAmount
                  anchors.right: parent.right
                  anchors.baseline: txName.baseline
                  textFormat: Text.PlainText
                  text: txRow.modelData.amount_text || ""
                  color: txRow.modelData.pending === true ? ac.muted : ac.foreground
                  font.family: ac.fontFamily
                  font.pixelSize: Style.font.body
                  font.features: ({ "tnum": 1 })
                }
              }
            }
          }
        }
      }
    }

    Text {
      visible: text !== ""
      width: parent.width
      textFormat: Text.PlainText
      text: ac.doc ? (ac.doc.empty_text || "") : ""
      color: ac.muted
      font.family: ac.fontFamily
      font.pixelSize: Style.font.body
      topPadding: Style.space(6)
    }

    // ---- footer: the clock, and the door to Monzo
    Item {
      width: parent.width
      height: Math.max(ac.doc ? checkedText.implicitHeight : 0, openLink.height)

      Text {
        id: checkedText
        anchors.left: parent.left
        anchors.verticalCenter: openLink.verticalCenter
        textFormat: Text.PlainText
        text: ac.doc ? (ac.doc.checked_text || "") : ""
        color: ac.muted
        font.family: ac.fontFamily
        font.pixelSize: Style.font.caption
        font.features: ({ "tnum": 1 })
      }

      Rectangle {
        id: openLink
        visible: openText.text !== ""
        anchors.right: parent.right
        anchors.top: parent.top
        width: visible ? openText.implicitWidth + Style.space(14) : 0
        height: openText.implicitHeight + Style.space(6)
        radius: height / 2
        color: openArea.containsMouse ? Style.hoverFillFor(ac.foreground, Color.accent, Color.urgent) : Style.normalFillFor(ac.foreground, Color.accent, Color.urgent)
        border.width: 1
        border.color: openArea.containsMouse ? Color.accent : Style.normalBorderFor(ac.foreground, Color.accent, Color.urgent)

        Text {
          id: openText
          anchors.centerIn: parent
          textFormat: Text.PlainText
          text: ac.doc ? (ac.doc.open_text || "") : ""
          color: openArea.containsMouse ? Color.accent : ac.foreground
          font.family: ac.fontFamily
          font.pixelSize: Style.font.caption
        }

        MouseArea {
          id: openArea
          anchors.fill: parent
          hoverEnabled: true
          cursorShape: Qt.PointingHandCursor
          onClicked: ac.openRequested()
        }
      }
    }
  }
}
