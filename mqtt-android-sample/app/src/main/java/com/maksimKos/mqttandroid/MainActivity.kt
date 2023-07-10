package com.maksimKos.mqttandroid

import android.graphics.Color
import android.icu.text.SimpleDateFormat
import android.icu.util.Calendar
import android.os.Build
import android.os.Bundle
import android.text.method.LinkMovementMethod
import android.util.Log
import android.widget.Toast
import androidx.annotation.RequiresApi
import androidx.annotation.StringRes
import androidx.appcompat.app.AppCompatActivity
import com.beust.klaxon.JsonReader
import com.beust.klaxon.Klaxon
import com.maksimKos.mqttandroid.mqtt.MqttManagerImpl
import com.maksimKos.mqttandroid.mqtt.MqttStatusListener
import kotlinx.android.synthetic.main.activity_main.*
import okhttp3.*
import org.eclipse.paho.client.mqttv3.MqttMessage
import java.io.IOException
import java.io.StringReader


const val TAG = "msg"
const val serverUri = "tcp://92.53.105.143:1883"
const val subscriptionTopic = "cam/#"

class Data(val people: String, val time: String, val url: String)
class BD_Data(val camera_id: String, val people: String, val photo_url: String, val time_detect: String)

class MainActivity : AppCompatActivity() {

    private var clientId = "MyAndroidClientId" + System.currentTimeMillis()

    lateinit var mqttManager: MqttManagerImpl

    private val client = OkHttpClient()

    @RequiresApi(Build.VERSION_CODES.N)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val format = SimpleDateFormat("yyyy-MM-dd hh:mm:ss")

        mqttManager = MqttManagerImpl(
                applicationContext,
                serverUri,
                clientId,
                arrayOf(subscriptionTopic),
                IntArray(1) { 0 })
        mqttManager.init()
        initMqttStatusListener()
        mqttManager.connect()

        textView.movementMethod = LinkMovementMethod.getInstance()
        textView.setLinkTextColor(Color.BLUE);

        buttonSubmit.setOnClickListener {

            //TO DO: NO SUPPORT FOR APACHE
            //val httpTransport: HttpTransport = ApacheHttpClientTransport()
            //val client = ClickHouseRawClient(httpTransport)
            //var res = client.select("http://92.53.105.143:18123", "SELECT * FROM security_db.detection\n" +
            //        "WHERE (time_detect BETWEEN '2023-06-03 20:23:02' AND '2023-06-03 20:23:04')")

            val day_from = (datePicker_from.dayOfMonth)
            val month_from = (datePicker_from.month)
            val year_from = (datePicker_from.year)
            val hour_from = (timePicker_from.hour)
            val min_from =(timePicker_from.minute)

            val calendar: Calendar = Calendar.getInstance()
            calendar.set(year_from, month_from, day_from, hour_from, min_from, 0)

            val strDate_from: String = format.format(calendar.time)

            val day_to = (datePicker_to.dayOfMonth)
            val month_to = (datePicker_to.month)
            val year_to = (datePicker_to.year)

            val hour_to = (timePicker_from.hour)
            val min_to =(timePicker_from.minute)

            calendar.set(year_to, month_to, day_to, hour_to, min_to, 0)

            val strDate_to: String = format.format(calendar.time)

            // url of the api through which we get random dog images
            var url = "http://92.53.105.143:11000/$strDate_from/$strDate_to"
            url = "http://92.53.105.143:11000/2023-06-03%2020:23:02/2023-06-03%2020:23:04"
            println(url)

            val request = Request.Builder()
                .url(url)
                .build()

            client.newCall(request).enqueue(object : Callback {
                override fun onFailure(call: Call, e: IOException) {}
                override fun onResponse(call: Call, response: Response) {
                    val ans = (response.body()?.string())
                    if (ans != null) {
                        parse_bd(ans)
                    }
                }
            })
        }

        buttonSub.setOnClickListener {
            mqttManager.init()
            mqttManager.connect()
            mqttManager.subscribeToTopic(arrayOf(subscriptionTopic))
        }

        buttonUnsub.setOnClickListener {
            mqttManager.unSubscribeToTopic(arrayOf(subscriptionTopic))
        }

        buttonClean.setOnClickListener {
            textView.text = ""
        }
    }

    private fun parse_bd(res: String){
        val klaxon = Klaxon()
        val border = "-------------------------------------------------"
        JsonReader(StringReader(res)).use { reader ->
            val result = arrayListOf<BD_Data>()
            reader.beginArray {
                while (reader.hasNext()) {
                    val person = klaxon.parse<BD_Data>(reader)
                    if (person != null) {
                        var res = "From: [${person.camera_id}] \ndetected: \t[ ${person.people} ] \ntime: \t[${person.time_detect}]" +
                                "\ncheck: \t[${person.photo_url}]"
                        textView.text = "\n" + border + "\n" + res + "\n" + border + "\n" + textView.text
                    }
                }
            }
        }
    }

    private fun initMqttStatusListener() {
        mqttManager.mqttStatusListener = object : MqttStatusListener {
            override fun onConnectComplete(reconnect: Boolean, serverURI: String) {
                if (reconnect) {
                    displayInDebugLog("Reconnected to : $serverURI")
                } else {
                    displayInDebugLog("Connected to: $serverURI")
                }
            }

            override fun onConnectFailure(exception: Throwable) {
                displayInDebugLog("Failed to connect")
            }

            override fun onConnectionLost(exception: Throwable) {
                displayInDebugLog("The Connection was lost.")
            }

            override fun onMessageArrived(topic: String, message: MqttMessage) {
                displayInMessagesList(String(message.payload), topic)
            }

            override fun onTopicSubscriptionSuccess() {
                displayInDebugLog("Subscribed!")
            }

            override fun onTopicSubscriptionError(exception: Throwable) {
                displayInDebugLog("Failed to subscribe")
            }
        }
    }

    private fun displayInMessagesList(message: String, topic: String) {
        val result = Klaxon().parse<Data>(message)
        if (result != null) {
            val border = "-------------------------------------------------"
            var res = "From: [${topic}] \ndetected: \t${result.people} \ntime: \t[${result.time}]" +
                    "\ncheck: \t[${result.url}]"
            textView.text = "\n" + border + "\n" + res + "\n" + border + "\n" + textView.text
        }
    }

    private fun displayInDebugLog(message: String) {
        Log.i(TAG, message)
    }

    /*private fun submitMessage() {
        val message = editTextMessage.text.toString()
        if (TextUtils.isEmpty(message)) {
            displayToast(R.string.general_please_write_some_message)
            return
        }
        mqttManager.sendMessage(message, publishTopic)
        clearInputField()
    }*/

    private fun displayToast(@StringRes messageId: Int) {
        Toast.makeText(this, messageId, Toast.LENGTH_LONG).show()
    }

}