import UIKit
import MQTTClient

struct row_bd: Decodable {
    let camera_id: String
    let people: String
    let photo_url: String
    let time_detect: String
}

class ViewController: UIViewController {
    
    let server = "92.53.105.143"
    let port: UInt32 = 1883
    let subscriptionTopic = "cam/#"
    @IBOutlet weak var clear: UIButton!
    @IBOutlet weak var sub: UIButton!
    @IBOutlet weak var unsub: UIButton!
    @IBOutlet weak var text_view: UITextView!
    @IBOutlet weak var bd: UIButton!
    @IBOutlet weak var from_date: UIDatePicker!
    @IBOutlet weak var to_date: UIDatePicker!
    
    private let session = MQTTSession()!
    
    let df = DateFormatter()
    
    override func viewDidLoad() {
        super.viewDidLoad()
        createMqttSocketTransport()
        text_view.isUserInteractionEnabled = true
        text_view.isEditable = false
        text_view.linkTextAttributes = [
            .foregroundColor: UIColor.blue,
            .underlineStyle: NSUnderlineStyle.single.rawValue
        ]
        df.dateFormat = "yyyy-MM-dd HH:mm:ss"
    }
    
    @IBAction func onSubmitClicked(_ sender: UIButton) {
        
        if sender == clear {
            text_view.text = ""
        }
        
        if sender == bd {
            //get_val_bd()
            get_val_bd_hhtp()
        }
        
        if sender == sub {
            subscribeToTopic()
            connectToMqtt()
        }
        
        if sender == unsub {
            unsubscribeToTopic()
            self.session.disconnect()
        }
    }
    
}

extension ViewController: MQTTSessionDelegate{
    
    func createMqttSocketTransport() {
        let transport = MQTTCFSocketTransport()
        transport.tls = false
        transport.port = port
        transport.host = server
        
        session.clientId = "IosClient_\(NSDate().timeIntervalSince1970)"
        session.transport = transport
        session.delegate = self
    }
    
    func handleEvent(_ session: MQTTSession!, event eventCode: MQTTSessionEvent, error: Error!) {
        switch eventCode {
        case .connected:
            TRACE("Connected")
            subscribeToTopic()
        case .connectionClosed:
            TRACE("Closed")
        case .connectionClosedByBroker:
            TRACE("Closed by Broker")
        case .connectionError:
            TRACE("Error")
        case .connectionRefused:
            TRACE("Refused")
        case .protocolError:
            TRACE("Protocol Error")
        }
    }
    
    func newMessage(_ session: MQTTSession!, data: Data!, onTopic topic: String!, qos: MQTTQosLevel, retained: Bool, mid: UInt32) {
        let message = String(decoding: data, as: UTF8.self)
        let mess = convertToDictionary(text:message)
        
        let people = mess?["people"] ?? "None"
        let time = mess?["time"] ?? "None"
        let url = mess?["url"] ?? "None"
        
        TRACE("\n topic: { \(topic!)} data: {\(message)}")
        displayMessageLog("\n Click here to see cam: [\(topic!)] people: \(people) time: [\(time)] \n", url as! String)
    }
    
    func subAckReceived(_ session: MQTTSession!, msgID: UInt16, grantedQoss qoss: [NSNumber]!) {
        TRACE("\n subAckReceived")
    }
    
    func unsubAckReceived(_ session: MQTTSession!, msgID: UInt16) {
        TRACE("\n unsubAckReceived")
    }
    
    func unsubscribeToTopic() {
        session.unsubscribeTopic(subscriptionTopic)
    }
    
    func connectToMqtt() {
        self.session.connect()
    }
    
    func subscribeToTopic() {
        session.subscribe(toTopic: subscriptionTopic, at: .atMostOnce)
    }
    
    func get_val_bd_hhtp() {
        
        var blogPosts: [row_bd]?
        // Create URL
        let from = df.string(from: from_date.date)
        let to = df.string(from: to_date.date)
        
        let url_str = "http://92.53.105.143:11000/\(from)/\(to)".addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed)

        let url = URL(string: url_str!)
        guard let requestUrl = url else { fatalError() }
        var request = URLRequest(url: requestUrl)
        request.httpMethod = "GET"
        let sem = DispatchSemaphore.init(value: 0)
        let task = URLSession.shared.dataTask(with: request) { (data, response, error) in
            defer { sem.signal() }
            if let error = error {
                print("Error took place \(error)")
                return
            }
            
            if let response = response as? HTTPURLResponse {
                print("Response HTTP Status code: \(response.statusCode)")
            }
            
            // Convert HTTP Response Data to a simple String
            if let data = data, let _ = String(data: data, encoding: .utf8) {
                blogPosts = try! JSONDecoder().decode([row_bd].self, from: data)
            }
        }
        task.resume()
        sem.wait()
        for (_, element) in blogPosts!.enumerated() {
           let post: row_bd = element
            self.displayMessageLog("\n Click here to see cam: [\(post.camera_id)] people: [\(post.people)] time: [\(post.time_detect)] \n", (post.photo_url))
        }
    }
    
    /*func get_val_bd() {
        
        let from = df.string(from: from_date.date)
        let to = df.string(from: to_date.date)
        
        let sql_req = "SELECT * FROM security_db.detection WHERE (time_detect BETWEEN '\(from)' AND '\(to)')"
    
        //print(sql_req)
        
        do {
            let conn = try connection.wait()
        let ans = try conn.query(sql: sql_req).map { res -> ([String], [String], [String], [ClickHouseDateTime]) in
            let cams = (res.columns.first(where: {$0.name == "camera_id"})!.values as? [String])
            //print(cams as Any)
            
            let people = (res.columns.first(where: {$0.name == "people"})!.values as? [String])
            //print(people as Any)
            
            let photo_url = (res.columns.first(where: {$0.name == "photo_url"})!.values as? [String])
            //print(photo_url as Any)
            
            let time_detect = (res.columns.first(where: {$0.name == "time_detect"})!.values as? [ClickHouseDateTime])
            //print(time_detect as Any)
            return (cams!, people!, photo_url!, time_detect!);
        }.wait()
            let c = ans.0
            let p = ans.1
            let ph = ans.2
            let t = ans.3
            
            for i in 0..<ans.0.count{
                displayMessageLog("\n Click here to see cam: [\(c[i])] people: [\(p[i])] time: [\(t[i])] \n", (ph[i]))
            }
        }
        
        catch {
            print(error)
        }
    }*/
    
    
}

extension ViewController {
    func TRACE(_ message: String = "", fun: String = #function) {
        print("[TRACE] [\(message)")
    }
    
    func displayAlert(_ title: String, message: String) {
        let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "Cancel", style: .cancel, handler: nil))
        self.present(alert, animated: true)
    }
    
    func displayMessageLog(_ message: String, _ in_url: String) {
        
        let attributedString = NSMutableAttributedString(string: message)
        let url = URL(string: in_url)!

        attributedString.setAttributes([.link: url], range: NSMakeRange(2, 10))
        
        let previous = text_view.attributedText.mutableCopy() as! NSMutableAttributedString
        attributedString.append(previous)
        
        text_view.attributedText = attributedString

        //text_view.attributedText = attributedString.append(("\n" + (text_view.attributedText))
        
        //text_view.text = message + "\n" + (text_view.text ?? "")
        
    }
    
    func convertToDictionary(text: String) -> [String: Any]? {
            if let data = text.data(using: .utf8) {
                do {
                    return try JSONSerialization.jsonObject(with: data, options: []) as? [String: Any]
                } catch {
                    print(String(describing: error))
                }
            }
            return nil
        }
    
    /*func clearInputField() {
        messageInputField.text = ""
    }*/
}


